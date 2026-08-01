// Live geometry knob panel (dev aid). Each slider writes a CSS custom property
// on :root so the ErgoDox thumb geometry can be tuned in the browser. Omitted
// from the published build (see the --no-panel flag in render_keymap.py).
(function geometryKnobs() {
  const root = document.documentElement;
  const readout = document.getElementById('k-out');

  // slider id -> [CSS custom property, unit]
  const knobs = {
    'k-gap': ['--board-gap', 'px'],
    'k-inset': ['--thumb-inset', 'px'],
    'k-top': ['--thumb-top', 'px'],
    'k-rot': ['--thumb-rot', 'deg'],
  };

  const valueOf = (id) => document.getElementById(id).value;

  function refreshReadout() {
    readout.textContent =
      `gap ${valueOf('k-gap')} · inset ${valueOf('k-inset')}` +
      ` · top ${valueOf('k-top')} · angle ${valueOf('k-rot')}`;
  }

  for (const [id, [property, unit]] of Object.entries(knobs)) {
    const slider = document.getElementById(id);
    const output = document.getElementById(id + '-o');
    const apply = () => {
      root.style.setProperty(property, slider.value + unit);
      output.textContent = slider.value;
      refreshReadout();
    };
    slider.addEventListener('input', apply);
    apply();
  }

  document.getElementById('k-toggle').addEventListener('click', function () {
    const panel = document.getElementById('knobs');
    panel.classList.toggle('collapsed');
    this.textContent = panel.classList.contains('collapsed') ? '+' : '–';
  });

  document.getElementById('k-copy').addEventListener('click', function () {
    if (navigator.clipboard) navigator.clipboard.writeText(readout.textContent);
    this.textContent = 'copied';
    setTimeout(() => { this.textContent = 'copy values'; }, 1100);
  });
})();
