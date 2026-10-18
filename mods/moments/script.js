// Моменты: свои закладки на секунды внутри серии.
animebuffer.onVideo(function (video) {
  if (document.getElementById('abx-mom-btn')) return;

  var key = 'm:' + location.pathname + location.search;
  var items = animebuffer.storage.get(key, []);

  var btn = document.createElement('button');
  btn.id = 'abx-mom-btn';
  btn.textContent = '◆';

  var panel = document.createElement('div');
  panel.id = 'abx-mom-panel';
  panel.hidden = true;

  var fmt = function (sec) {
    var s = Math.floor(sec);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var r = s % 60;
    var tail = (m < 10 && h > 0 ? '0' : '') + m + ':' + (r < 10 ? '0' : '') + r;
    return h > 0 ? h + ':' + tail : tail;
  };

  var save = function () {
    animebuffer.storage.set(key, items);
    btn.classList.toggle('abx-has', items.length > 0);
  };

  var render = function () {
    panel.textContent = '';
    var add = document.createElement('button');
    add.className = 'abx-add';
    add.textContent = '＋ Момент на ' + fmt(video.currentTime || 0);
    add.onclick = function () {
      items.push({ t: Math.floor(video.currentTime || 0), label: '' });
      items.sort(function (a, b) { return a.t - b.t; });
      save();
      render();
      animebuffer.toast('Момент сохранён');
    };
    panel.appendChild(add);

    if (items.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'abx-empty';
      empty.textContent = 'Пока пусто. Поставь видео на нужную секунду и нажми кнопку выше.';
      panel.appendChild(empty);
    }

    items.forEach(function (item, i) {
      var row = document.createElement('div');
      row.className = 'abx-row';

      var go = document.createElement('button');
      go.className = 'abx-go';
      go.textContent = fmt(item.t);
      go.onclick = function () {
        video.currentTime = item.t;
        video.play();
        panel.hidden = true;
      };

      var input = document.createElement('input');
      input.type = 'text';
      input.placeholder = 'Подпись';
      input.value = item.label;
      input.onchange = function () { item.label = input.value.trim(); save(); };

      var del = document.createElement('button');
      del.className = 'abx-del';
      del.textContent = '✕';
      del.onclick = function () { items.splice(i, 1); save(); render(); };

      row.appendChild(go);
      row.appendChild(input);
      row.appendChild(del);
      panel.appendChild(row);
    });
  };

  btn.onclick = function () {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) render();
  };

  document.body.appendChild(panel);
  document.body.appendChild(btn);
  btn.classList.toggle('abx-has', items.length > 0);
});
