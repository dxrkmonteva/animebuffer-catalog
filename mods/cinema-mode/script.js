// Режим кино: пока видео играет, на <html> стоит класс abx-cinema,
// а стили из style.css затемняют всё вокруг плеера.
animebuffer.onVideo(function (video) {
  var root = document.documentElement;
  var on = function () { root.classList.add('abx-cinema'); };
  var off = function () { root.classList.remove('abx-cinema'); };

  video.addEventListener('play', on);
  video.addEventListener('playing', on);
  video.addEventListener('pause', off);
  video.addEventListener('ended', off);
  if (!video.paused) on();
});
