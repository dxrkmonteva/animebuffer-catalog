// Заметки к серии: кнопка в углу, заметка хранится по адресу страницы.
animebuffer.ready(function () {
  var keyNow = function () { return 'note:' + location.hostname + location.pathname; };

  var btn = document.createElement('button');
  btn.id = 'abx-note-btn';
  btn.textContent = '✎';

  var panel = document.createElement('div');
  panel.id = 'abx-note-panel';
  panel.hidden = true;

  var area = document.createElement('textarea');
  area.placeholder = 'Заметка к этой серии...';

  var save = document.createElement('button');
  save.textContent = 'Сохранить';

  var refresh = function () {
    var text = animebuffer.storage.get(keyNow(), '');
    area.value = text;
    btn.classList.toggle('abx-has', text.length > 0);
  };

  btn.onclick = function () {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
      refresh();
      area.focus();
    }
  };

  save.onclick = function () {
    var text = area.value.trim();
    animebuffer.storage.set(keyNow(), text);
    btn.classList.toggle('abx-has', text.length > 0);
    panel.hidden = true;
    animebuffer.toast(text ? 'Заметка сохранена' : 'Заметка удалена');
  };

  panel.appendChild(area);
  panel.appendChild(save);
  document.body.appendChild(panel);
  document.body.appendChild(btn);
  refresh();
});
