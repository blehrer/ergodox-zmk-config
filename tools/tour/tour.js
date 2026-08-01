// Keymap tour — page interactivity. Dependency-free; inlined into the page at
// build time so the published site stays a single self-contained file.

// Highlight the nav link for whichever layer section is currently in view.
(function highlightActiveLayer() {
  const links = [...document.querySelectorAll('nav.layers a')];
  const sections = links
    .map(link => document.getElementById(link.dataset.target))
    .filter(Boolean);

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      links.forEach((link) =>
        link.classList.toggle('active', link.dataset.target === entry.target.id));
    }
  }, { rootMargin: '-45% 0px -50% 0px' });

  sections.forEach((section) => observer.observe(section));
})();

// Scale each stacked half-card to fit the viewport. Below the stacking
// breakpoint the two halves become vertical cards of a fixed content width;
// CSS calc() can't derive a unitless scale factor from vw, so it's computed
// here and exposed as the --scale custom property. CONTENT_WIDTH and CHROME
// must stay in sync with the stacked-mode rules in tour.css (--cw and the card
// + scroll padding around the stage).
(function scaleStackedCards() {
  const CONTENT_WIDTH = 562;
  const CHROME = 64;
  const MIN_SCALE = 0.4;
  const stacked = window.matchMedia('(max-width:960px)');
  const boards = [...document.querySelectorAll('.board')];

  function fit() {
    const available = document.documentElement.clientWidth - CHROME;
    const scale = stacked.matches
      ? Math.max(MIN_SCALE, Math.min(1, available / CONTENT_WIDTH))
      : 1;
    boards.forEach((board) => board.style.setProperty('--scale', String(scale)));
  }

  fit();
  window.addEventListener('resize', fit, { passive: true });
  if (stacked.addEventListener) stacked.addEventListener('change', fit);
})();
