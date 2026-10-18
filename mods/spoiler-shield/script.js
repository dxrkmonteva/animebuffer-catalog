// Антиспойлер: размывает самые внешние блоки описаний и комментариев.
animebuffer.ready(function () {
  var SEL = '[class*="comment" i], [id*="comment" i], [class*="spoiler" i], [class*="descr" i], [itemprop="description"]';
  var root = document.documentElement;
  var on = animebuffer.storage.get('on', true);

  var btn = document.createElement('button');
  btn.id = 'abx-sp-btn';
  btn.textContent = '👁';

  var apply = function () {
    root.classList.toggle('abx-sp-on', on);
    btn.classList.toggle('abx-on', on);
  };

  // Блок подходит, если это не вся страница и внутри нет плеера или навигации.
  var fits = function (el) {
    if (el === document.body || el === root) return false;
    if (el.querySelector('video, iframe, nav, header, form')) return false;
    return true;
  };

  // Помечаем только внешние блоки, чтобы вложенные не размывались дважды.
  var mark = function () {
    var list = document.querySelectorAll(SEL);
    for (var i = 0; i < list.length; i++) {
      var el = list[i];
      if (el.classList.contains('abx-sp')) continue;
      var parent = el.parentElement ? el.parentElement.closest(SEL) : null;
      if (parent && fits(parent)) continue;
      if (fits(el)) el.classList.add('abx-sp');
    }
  };

  document.addEventListener('click', function (e) {
    if (!on) return;
    var hit = e.target.closest ? e.target.closest('.abx-sp') : null;
    if (hit && !hit.classList.contains('abx-shown')) {
      e.preventDefault();
      e.stopPropagation();
      hit.classList.add('abx-shown');
    }
  }, true);

  btn.onclick = function () {
    on = !on;
    animebuffer.storage.set('on', on);
    if (!on) {
      var open = document.querySelectorAll('.abx-shown');
      for (var i = 0; i < open.length; i++) open[i].classList.remove('abx-shown');
    }
    apply();
  };

  var pending = 0;
  new MutationObserver(function () {
    if (pending) return;
    pending = setTimeout(function () { pending = 0; mark(); }, 600);
  }).observe(document.body, { childList: true, subtree: true });

  document.body.appendChild(btn);
  mark();
  apply();
});
