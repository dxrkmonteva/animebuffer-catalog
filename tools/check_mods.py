#!/usr/bin/env python3
"""
Проверка модов каталога AnimeBuffer и сборка index.json.

  python tools/check_mods.py --validate   проверить все моды (для заявок), index.json не трогать
  python tools/check_mods.py --write      проверить и пересобрать index.json
  python tools/check_mods.py --check      проверить и убедиться, что index.json актуален

Правила анализа кода ДОЛЖНЫ совпадать с приложением (ModAnalysis.kt).
Менять их можно только вместе: иначе приложение откажется ставить моды, прошедшие проверку здесь.
"""
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODS = ROOT / "mods"
INDEX = ROOT / "index.json"
CONFIG = ROOT / "catalog.config.json"

MAX_FILE = 128 * 1024
MAX_SCREENSHOT = 512 * 1024
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
FILE_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
FRAMES = {"top", "all"}
RUN_AT = {"start", "end"}

KNOWN_API = {"css", "hide", "ready", "log", "storage", "waitFor", "onVideo", "toast", "version", "modId"}
PERMS_ALL = ["style", "dom", "video", "storage", "network", "cookies", "passwords", "clipboard"]
# эти разрешения опасны: на карточке они красные, и куратор обязан понимать, зачем они моду
PERMS_DANGEROUS = {"network", "cookies", "passwords", "clipboard"}

# ---- запрещено полностью (обфускация, динамический код, побег из «песочницы» API) ----
HARD = [
    (r"\beval\b", "eval: выполнение строки как кода"),
    (r"\bFunction\s*\(", "Function(...): выполнение строки как кода"),
    (r"\batob\s*\(", "atob: расшифровка спрятанного кода"),
    (r"\bfromCharCode\b", "fromCharCode: сборка кода из символов"),
    (r"\bunescape\s*\(", "unescape: расшифровка строк"),
    (r"\b(window|globalThis|self|top|parent|frames)\s*\[", "доступ к глобальным объектам через [ ]"),
    (r"\[\s*['\"\x60][^'\"\x60]*['\"\x60]\s*\+", "имя свойства, собранное из кусков строки"),
    (r"\.\s*constructor\b", ".constructor: обход запретов"),
    (r"\bwith\s*\(", "with(...)"),
    (r"\bset(Timeout|Interval)\s*\(\s*['\"\x60]", "setTimeout/setInterval со строкой вместо функции"),
    (r"\bimport\s*\(", "динамический import()"),
    (r"javascript\s*:", "адрес javascript:"),
    (r"(\\x[0-9a-fA-F]{2}){4}", "цепочка \\x-кодов (спрятанный текст)"),
    (r"(\\u[0-9a-fA-F]{4}){4}", "цепочка \\u-кодов (спрятанный текст)"),
    (r"\b(Reflect|Proxy)\b", "Reflect/Proxy"),
    (r"__proto__", "__proto__"),
    (r"\bdocument\s*\.\s*write", "document.write"),
    (r"\bpostMessage\b", "postMessage: передача данных между окнами"),
    (r"\bwindow\s*\.\s*open\b", "window.open"),
    (r"\b(geolocation|getUserMedia|mediaDevices|requestPermission|Notification)\b", "доступ к устройству/уведомлениям"),
]
# animebuffer нельзя передавать как значение: тогда не видно, какие методы он вызывает
BARE_API = re.compile(r"\banimebuffer\b(?!\s*\.)")
API_CALL = re.compile(r"\banimebuffer\s*\.\s*([A-Za-z_]\w*)")
MAX_LINE = 800

# ---- что мод умеет (разрешения определяются по коду, а не со слов автора) ----
PERM_RULES = {
    "dom": [r"\bdocument\b", r"\bquerySelector", r"\bgetElement", r"\bcreateElement\b", r"\binnerHTML\b", r"\binsertAdjacentHTML\b"],
    "video": [r"\bcurrentTime\b", r"\bplaybackRate\b", r"\bHTMLVideoElement\b", r"\brequestFullscreen\b", r"['\"\x60]video['\"\x60]", r"<\s*video\b"],
    "storage": [r"\blocalStorage\b", r"\bsessionStorage\b", r"\bindexedDB\b", r"\bcaches\b"],
    "network": [
        r"\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|importScripts|Worker|SharedWorker|serviceWorker)\b",
        r"\bnew\s+Image\s*\(",
        r"\.\s*src\s*=",
        r"setAttribute\s*\(\s*['\"\x60](src|href|srcset|action)['\"\x60]",
        r"createElement\s*\(\s*['\"\x60](script|iframe|img|link|embed|object|form)['\"\x60]",
        r"\blocation\s*(\.\s*(href|assign|replace)\s*=|=(?!=))",
        r"<\s*(img|script|iframe|link|object|embed|audio|source|form)\b[^>]*\b(src|href|action)\s*=",
    ],
    "cookies": [r"\bcookie\b", r"\bcookieStore\b"],
    "passwords": [r"password"],
    "clipboard": [r"\bclipboard\b", r"execCommand\s*\(\s*['\"\x60](copy|cut|paste)"],
}
CSS_NETWORK = [r"url\(\s*['\"]?\s*(https?:)?//", r"@import"]


def analyze(manifest, css, js):
    """Возвращает (api, perms, hard) — множества методов API, разрешений и список запретов."""
    hard = []
    api = set()
    perms = set()

    for pattern, text in HARD:
        if re.search(pattern, js):
            hard.append(text)
    if BARE_API.search(js):
        hard.append("animebuffer передаётся как значение: используй только animebuffer.метод(...)")
    for m in API_CALL.finditer(js):
        name = m.group(1)
        if name in KNOWN_API:
            api.add(name)
        else:
            hard.append("неизвестный метод animebuffer." + name)
    for n, line in enumerate(js.split("\n"), 1):
        if len(line) > MAX_LINE:
            hard.append("строка %d длиннее %d символов (похоже на минифицированный/спрятанный код)" % (n, MAX_LINE))
            break

    if css.strip() or api & {"css", "hide"}:
        perms.add("style")
    if "waitFor" in api:
        perms.add("dom")
    if "onVideo" in api:
        perms.add("video")
    if "storage" in api:
        perms.add("storage")
    for perm, patterns in PERM_RULES.items():
        flags = re.I if perm == "passwords" else 0
        if any(re.search(p, js, flags) for p in patterns):
            perms.add(perm)
    if any(re.search(p, css, re.I) for p in CSS_NETWORK):
        perms.add("network")
    return api, perms, hard


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bundle_hash(files: dict) -> str:
    lines = "".join("%s:%s\n" % (n, files[n]) for n in sorted(files))
    return sha256(lines.encode("utf-8"))


def check_mod(mod_dir: Path):
    """Возвращает (entry, errors, warnings)."""
    errors, warnings = [], []
    mid = mod_dir.name
    if not ID_RE.match(mid):
        errors.append("имя папки должно быть вида my-mod-name (a-z, 0-9, дефис)")
    mf = mod_dir / "manifest.json"
    if not mf.is_file():
        return None, ["нет manifest.json"], warnings
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except Exception as e:
        return None, ["manifest.json не читается: %s" % e], warnings

    if m.get("id") != mid:
        errors.append("id в manifest.json (%r) должен совпадать с именем папки (%r)" % (m.get("id"), mid))
    for key in ("name", "author", "version", "description"):
        if not isinstance(m.get(key), str) or not m[key].strip():
            errors.append("нет поля %s" % key)
    if len(m.get("name", "")) > 60:
        errors.append("name длиннее 60 символов")
    if len(m.get("description", "")) > 300:
        errors.append("description длиннее 300 символов")
    if len(m.get("author", "")) > 60:
        errors.append("author длиннее 60 символов")
    if len(m.get("version", "")) > 20:
        errors.append("version длиннее 20 символов")
    matches = m.get("matches")
    if not isinstance(matches, list) or not matches or not all(isinstance(x, str) and 0 < len(x) <= 100 for x in matches):
        errors.append("matches: нужен непустой список сайтов")
        matches = []
    elif len(matches) > 30:
        errors.append("matches: не больше 30 записей")
    elif "*" in matches:
        warnings.append("мод работает на ВСЕХ сайтах (matches содержит *)")
    if m.get("frames", "top") not in FRAMES:
        errors.append("frames: top или all")
    if m.get("runAt", "end") not in RUN_AT:
        errors.append("runAt: start или end")

    # файлы: только манифест, css, js и необязательный скриншот
    css_name, js_name, shot_name = m.get("css", ""), m.get("js", ""), m.get("screenshot", "")
    allowed = {"manifest.json"}
    for label, name in (("css", css_name), ("js", js_name), ("screenshot", shot_name)):
        if name:
            if not isinstance(name, str) or not FILE_RE.match(name) or name.startswith("."):
                errors.append("%s: недопустимое имя файла %r" % (label, name))
            else:
                allowed.add(name)
    if not css_name and not js_name:
        errors.append("нужен хотя бы один из css/js")
    actual = {p.name for p in mod_dir.iterdir()}
    for extra in sorted(actual - allowed):
        errors.append("лишний файл %r: в папке мода разрешены только manifest.json, css, js и скриншот" % extra)
    for p in mod_dir.iterdir():
        if p.is_dir():
            errors.append("вложенные папки не разрешены: %s" % p.name)

    files = {}
    texts = {"css": "", "js": ""}
    for name in sorted(allowed & actual):
        p = mod_dir / name
        if not p.is_file():
            continue
        data = p.read_bytes()
        limit = MAX_SCREENSHOT if name == shot_name else MAX_FILE
        if len(data) > limit:
            errors.append("%s слишком большой (%d КБ, лимит %d КБ)" % (name, len(data) // 1024, limit // 1024))
        files[name] = sha256(data)
        if name in (css_name, js_name):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                errors.append("%s: не UTF-8" % name)
                continue
            texts["css" if name == css_name else "js"] = text
    for label, name in (("css", css_name), ("js", js_name)):
        if name and name not in actual:
            errors.append("файл %s из manifest.json не найден" % name)

    api, perms, hard = analyze(m, texts["css"], texts["js"])
    for h in hard:
        errors.append("запрещено в каталоге: " + h)

    declared_perms = m.get("permissions")
    declared_api = m.get("api")
    if not isinstance(declared_perms, list) or not all(x in PERMS_ALL for x in declared_perms):
        errors.append("permissions: список из %s" % ", ".join(PERMS_ALL))
        declared_perms = []
    if not isinstance(declared_api, list) or not all(isinstance(x, str) for x in declared_api):
        errors.append("api: список методов animebuffer, которые использует мод")
        declared_api = []
    for p in sorted(perms - set(declared_perms)):
        errors.append("мод умеет «%s», но не заявляет это в permissions" % p)
    for p in sorted(set(declared_perms) - perms):
        warnings.append("permissions заявляет «%s», но в коде это не найдено" % p)
    for a in sorted(api - set(declared_api)):
        errors.append("мод вызывает animebuffer.%s, но не заявляет это в api" % a)
    for a in sorted(set(declared_api) - api):
        warnings.append("api заявляет «%s», но в коде вызова нет" % a)
    danger = sorted(perms & PERMS_DANGEROUS)
    if danger:
        warnings.append("ОПАСНЫЕ разрешения: %s — убедись, что они нужны моду" % ", ".join(danger))

    if errors:
        return None, errors, warnings

    entry = {
        "id": mid,
        "name": m["name"].strip(),
        "author": m["author"].strip(),
        "version": m["version"].strip(),
        "description": m["description"].strip(),
        "matches": matches,
        "frames": m.get("frames", "top"),
        "runAt": m.get("runAt", "end"),
        "permissions": [p for p in PERMS_ALL if p in perms],
        "api": sorted(api),
        "dir": "mods/" + mid,
        "files": files,
        "bundle": bundle_hash(files),
    }
    if shot_name:
        entry["screenshot"] = shot_name
    return entry, errors, warnings


def build():
    ok = True
    entries = []
    if not MODS.is_dir():
        print("нет папки mods/")
        return None
    for d in sorted(p for p in MODS.iterdir() if p.is_dir()):
        entry, errors, warnings = check_mod(d)
        status = "OK " if not errors else "ОШИБКА"
        print("[%s] %s" % (status, d.name))
        for w in warnings:
            print("    ! " + w)
        for e in errors:
            print("    x " + e)
        if errors:
            ok = False
        else:
            entries.append(entry)
    if not ok:
        return None

    cfg = {"name": "AnimeBuffer Catalog", "revoked": []}
    if CONFIG.is_file():
        cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    revoked = [str(x) for x in cfg.get("revoked", [])]
    return {
        "schema": 1,
        "name": cfg["name"],
        "updated": date.today().isoformat(),
        "revoked": revoked,
        "mods": entries,
    }


def same_content(a, b):
    a, b = dict(a), dict(b)
    a.pop("updated", None)
    b.pop("updated", None)
    return a == b


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--validate"
    index = build()
    if index is None:
        print("\nПроверка НЕ пройдена.")
        return 1
    old = None
    if INDEX.is_file():
        try:
            old = json.loads(INDEX.read_text(encoding="utf-8"))
        except Exception:
            old = None
    if mode == "--validate":
        print("\nВсе моды прошли проверку (%d)." % len(index["mods"]))
        return 0
    if mode == "--write":
        if old and same_content(old, index):
            index["updated"] = old.get("updated", index["updated"])
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("\nindex.json обновлён (%d модов)." % len(index["mods"]))
        return 0
    if mode == "--check":
        if not old or not same_content(old, index):
            print("\nindex.json устарел или изменён вручную. Запусти: python tools/check_mods.py --write")
            return 1
        print("\nindex.json актуален.")
        return 0
    print("режимы: --validate | --write | --check")
    return 2


if __name__ == "__main__":
    sys.exit(main())
