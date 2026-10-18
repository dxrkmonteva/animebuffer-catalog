/* AnimeBuffer Mod API example.
 * CSS does most of the work; JS only adds lightweight dynamic touches.
 */

(function () {
  animebuffer.ready(function () {
    // Mark the page so the theme can safely target its own dynamic layer.
    document.documentElement.setAttribute('data-animebuffer-theme', 'neon-aurora');

    // Add a tiny ambient glow layer without replacing page content.
    var glow = document.createElement('div');
    glow.setAttribute('data-animebuffer-neon-glow', '');
    glow.style.cssText = [
      'position:fixed',
      'inset:-25%',
      'pointer-events:none',
      'z-index:2147483000',
      'opacity:.28',
      'background:',
      'radial-gradient(circle at 20% 30%, rgba(85,232,255,.13), transparent 22%),',
      'radial-gradient(circle at 80% 65%, rgba(168,121,255,.12), transparent 25%)',
      'mix-blend-mode:screen',
      'transform:translate3d(0,0,0)',
      'animation:ab-neon-float 14s ease-in-out infinite alternate'
    ].join(';');

    var style = document.createElement('style');
    style.textContent = '@keyframes ab-neon-float{from{transform:translate3d(-1.5%, -1%, 0) scale(1)}to{transform:translate3d(1.5%, 1%, 0) scale(1.03)}}';
    (document.head || document.documentElement).appendChild(style);
    (document.body || document.documentElement).appendChild(glow);

    // Give dynamically created videos the same theme treatment.
    animebuffer.onVideo(function (video) {
      video.setAttribute('data-animebuffer-neon-video', '');
    });
  });
})();
