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

// Record intentional key gestures locally. No telemetry leaves the browser.
(function keypressTelemetry() {
  const STORAGE_KEY = 'ergodox-keymap-tour-events-v1';
  const keys = [...document.querySelectorAll('button.key[data-position]')];
  const sequenceLines = [...document.querySelectorAll('.keypress-sequence')];
  const resultLines = [...document.querySelectorAll('.keypress-results')];
  const copyButtons = [...document.querySelectorAll(
    '.keypress-copy-sequence, .keypress-copy-prompt'
  )];
  const menu = document.getElementById('gesture-menu');
  let selectedKey = null;

  function loadEvents() {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      if (!Array.isArray(stored)) return [];
      return stored.map((entry) => (
        entry.gesture === 'single' ? { ...entry, gesture: 'press' } : entry
      ));
    } catch {
      return [];
    }
  }

  let events = loadEvents();

  function saveEvents() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
    } catch {
      // The visible buffer still works when storage is unavailable or full.
    }
  }

  function sequenceToken(entry) {
    return `${entry.position}·${entry.gesture}`;
  }

  function resultToken(entry) {
    const tap = entry.tap || entry.binding;
    if (entry.gesture === 'double') return `${tap}${tap}`;
    if (entry.gesture === 'hold') {
      if (entry.behavior === 'lm' && entry.hold) return `${tap}+${entry.hold}`;
      return entry.hold || tap;
    }
    if (entry.gesture === 'tap-hold') return `${tap}→${entry.hold || tap}`;
    return tap;
  }

  function sequenceText() {
    return events.map(sequenceToken).join(' ');
  }

  function resultsText() {
    return events.map(resultToken).join(' ');
  }

  function updateBuffers() {
    const sequence = sequenceText();
    const results = resultsText();
    sequenceLines.forEach((line) => {
      line.textContent = sequence || 'No keys recorded';
      line.scrollLeft = line.scrollWidth;
    });
    resultLines.forEach((line) => {
      line.textContent = results;
      line.scrollLeft = line.scrollWidth;
    });
    copyButtons.forEach((button) => { button.disabled = !events.length; });
  }

  function closeMenu(restoreFocus = false) {
    if (menu.hidden) return;
    menu.hidden = true;
    if (selectedKey) {
      selectedKey.setAttribute('aria-expanded', 'false');
      if (restoreFocus) selectedKey.focus();
    }
    selectedKey = null;
  }

  function openMenu(key) {
    closeMenu();
    selectedKey = key;
    key.setAttribute('aria-expanded', 'true');
    menu.hidden = false;

    const rect = key.getBoundingClientRect();
    const gap = 8;
    let left = rect.right + gap;
    if (left + menu.offsetWidth > window.innerWidth - gap) {
      left = rect.left - menu.offsetWidth - gap;
    }
    const top = Math.min(
      window.innerHeight - menu.offsetHeight - gap,
      Math.max(gap, rect.top)
    );
    menu.style.left = `${Math.max(gap, left)}px`;
    menu.style.top = `${top}px`;
    menu.querySelector('button').focus();
  }

  function record(key, gesture) {
    const entry = {
      timestamp: new Date().toISOString(),
      layer: Number(key.dataset.layer),
      layerName: key.dataset.layerName,
      position: Number(key.dataset.position),
      side: key.dataset.side,
      binding: key.dataset.binding,
      behavior: key.dataset.behavior,
      gesture,
      tap: key.dataset.tap,
      hold: key.dataset.hold,
    };
    const targetMatches = key.dataset.targetLayer && (
      key.dataset.targetGesture === gesture ||
      (key.dataset.targetGesture === 'hold' && gesture === 'tap-hold')
    );
    if (targetMatches) entry.targetLayer = Number(key.dataset.targetLayer);

    events.push(entry);
    saveEvents();
    updateBuffers();
    closeMenu();

    if (targetMatches) location.hash = `layer-${entry.targetLayer}`;
  }

  function buildPrompt(sequence, results) {
    return `Key sequence: ${sequence}
Resolved tour result: ${results || '(none)'}

If the apps in scope have not been recorded:
- Ask: "Which programs should I have in scope for reconfiguring keybindings?"
- For each supplied app, determine the folders and files used for its configuration.

For each supplied app:
- Look up what ${sequence} does in its configuration.
- If it is unspecified and the app's defaults have not been cleared, determine its default behavior.
- Report: ${sequence} does ... in \${app}.

Ask me:
- What do you want ${sequence} to do?

Evaluate whether this conflicts with any supplied app. If conflicts exist, present concrete choices for resolving them. You may use additional key sequences copied from the keymap tour.`;
  }

  async function writeClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(textarea);
      textarea.select();
      const copied = document.execCommand('copy');
      textarea.remove();
      if (!copied) throw new Error('Clipboard copy failed');
    }
  }

  async function copyWithFeedback(text, button) {
    const label = button.getAttribute('aria-label');
    try {
      await writeClipboard(text);
      button.classList.add('copied');
      button.setAttribute('aria-label', 'Copied');
    } catch {
      button.classList.add('copy-failed');
      button.setAttribute('aria-label', 'Copy failed');
    }
    setTimeout(() => {
      button.classList.remove('copied', 'copy-failed');
      button.setAttribute('aria-label', label);
    }, 1100);
  }

  function clearEvents() {
    events = [];
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // The in-memory history and visible buffers are still cleared.
    }
    updateBuffers();
    closeMenu();
    location.hash = 'layer-0';
  }

  document.addEventListener('click', (event) => {
    const action = event.target.closest('#gesture-menu [data-gesture]');
    if (action && selectedKey) {
      record(selectedKey, action.dataset.gesture);
      return;
    }

    const key = event.target.closest('button.key[data-position]');
    if (key) {
      if (key.dataset.dual === 'true') openMenu(key);
      else {
        const behavior = key.dataset.behavior;
        const gesture = behavior === 'mo' || behavior === 'lm' ? 'hold' : 'press';
        record(key, gesture);
      }
      return;
    }

    const copySequence = event.target.closest('.keypress-copy-sequence');
    if (copySequence) {
      copyWithFeedback(sequenceText(), copySequence);
      return;
    }
    const copyPrompt = event.target.closest('.keypress-copy-prompt');
    if (copyPrompt) {
      copyWithFeedback(buildPrompt(sequenceText(), resultsText()), copyPrompt);
      return;
    }
    if (event.target.closest('.keypress-clear')) {
      clearEvents();
      return;
    }
    if (!menu.hidden) closeMenu(true);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) {
      event.preventDefault();
      closeMenu(true);
    }
  });

  window.addEventListener('resize', () => closeMenu(), { passive: true });
  window.addEventListener('scroll', () => closeMenu(), { passive: true });
  updateBuffers();
})();
