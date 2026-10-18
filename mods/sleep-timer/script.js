// Таймер сна: одна кнопка, по нажатию перебирает 15 → 30 → 45 → 60 → выкл.
animebuffer.onVideo(function () {
  if (document.getElementById('abx-sleep-btn')) return;

  var steps = [0, 15, 30, 45, 60];
  var index = 0;
  var endAt = 0;
  var timer = 0;

  var btn = document.createElement('button');
  btn.id = 'abx-sleep-btn';
  btn.textContent = '☾';

  var fade = document.createElement('div');
  fade.id = 'abx-sleep-fade';

  var label = function (ms) {
    var s = Math.max(0, Math.round(ms / 1000));
    var m = Math.floor(s / 60);
    var r = s % 60;
    return '☾ ' + m + ':' + (r < 10 ? '0' : '') + r;
  };

  var stop = function () {
    if (timer) { clearInterval(timer); timer = 0; }
    endAt = 0;
    btn.classList.remove('abx-on');
    btn.textContent = '☾';
    fade.classList.remove('abx-dark');
  };

  var finish = function () {
    var list = document.querySelectorAll('video');
    for (var i = 0; i < list.length; i++) list[i].pause();
    stop();
    index = 0;
    animebuffer.toast('Таймер сна: пауза. Спокойной ночи!');
  };

  var tick = function () {
    var left = endAt - Date.now();
    if (left <= 0) { finish(); return; }
    btn.textContent = label(left);
    // за 30 секунд до конца экран начинает плавно темнеть
    if (left < 30000) fade.classList.add('abx-dark');
  };

  btn.onclick = function () {
    index = (index + 1) % steps.length;
    stop();
    if (steps[index] === 0) {
      animebuffer.toast('Таймер сна выключен');
      return;
    }
    endAt = Date.now() + steps[index] * 60000;
    btn.classList.add('abx-on');
    tick();
    timer = setInterval(tick, 1000);
    animebuffer.toast('Пауза через ' + steps[index] + ' мин');
  };

  document.body.appendChild(fade);
  document.body.appendChild(btn);
});
