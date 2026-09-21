/* book-enhance.js — Parchment Reader behaviors
 * Adds: reading progress bar, back-to-top button, theme transition smoothness.
 * Idempotent: safe to run after mdBook's own book.js.
 */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    injectProgressBar();
    injectToTop();
    wireProgress();
    wireToTop();
  });

  /* ---- progress bar ---- */
  function injectProgressBar() {
    if (document.getElementById('prch-progress')) return;
    var bar = document.createElement('div');
    bar.id = 'prch-progress';
    bar.innerHTML = '<span></span>';
    document.body.appendChild(bar);
  }

  function wireProgress() {
    var fill = document.querySelector('#prch-progress > span');
    if (!fill) return;

    var ticking = false;
    function update() {
      var doc = document.documentElement;
      var scrolled = window.scrollY || doc.scrollTop;
      var total = (doc.scrollHeight - doc.clientHeight) || 1;
      var pct = Math.min(100, Math.max(0, (scrolled / total) * 100));
      fill.style.width = pct.toFixed(2) + '%';
      ticking = false;
    }
    function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
  }

  /* ---- back to top ---- */
  function injectToTop() {
    if (document.getElementById('prch-totop')) return;
    var btn = document.createElement('button');
    btn.id = 'prch-totop';
    btn.type = 'button';
    btn.title = '回到顶部';
    btn.setAttribute('aria-label', '回到顶部');
    btn.innerHTML = '&uarr;';
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    document.body.appendChild(btn);
  }

  function wireToTop() {
    var btn = document.getElementById('prch-totop');
    if (!btn) return;

    var last = false;
    function update() {
      var show = (window.scrollY || document.documentElement.scrollTop) > 480;
      if (show !== last) {
        btn.classList.toggle('show', show);
        last = show;
      }
    }
    window.addEventListener('scroll', update, { passive: true });
    update();
  }
})();
