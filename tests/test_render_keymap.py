import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_keymap", ROOT / "tools" / "render_keymap.py"
)
render_keymap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_keymap)

EXPECTED_SOURCE_SLUGS = frozenset(
    {
        "aerospace-directional-focus",
        "aerospace-directional-move",
        "aerospace-focus-cycle",
        "aerospace-layout-cycle",
        "aerospace-resize",
        "aerospace-service-mode",
        "aerospace-workspaces",
        "zellij-alt-quick-actions",
        "zellij-mode-cycle",
        "zellij-mode-entry",
        "zellij-new-tab",
        "zellij-keybind-tooltip",
        "zellij-quick-pane-tab",
        "zellij-quick-resize",
    }
)
SOURCE_SLUG_IN_URL = re.compile(
    r"github\.com/blehrer/dotfiles/search\?q=%22keymap-ref%3A\+([a-z][a-z0-9-]*)%22"
)


def layer_desc(keymap_text, short):
    for layer in render_keymap.parse_layers(keymap_text):
        if layer["short"] == short:
            return layer["desc"]
    raise KeyError(short)


def layer_notes_html(page, layer_idx):
    pattern = (
        rf'<section class="layer" id="layer-{layer_idx}">.*?'
        r'<details class="notes".*?<div class="desc">(.*?)</div>\s*</details>'
    )
    match = re.search(pattern, page, re.S)
    if not match:
        raise AssertionError(f"layer-{layer_idx} notes missing from tour page")
    return match.group(1)


def extract_source_slugs(text):
    return set(SOURCE_SLUG_IN_URL.findall(text))


class RenderNoteTextTest(unittest.TestCase):
    def test_https_github_link_escapes_ampersand_in_href(self):
        text = "[code search](https://github.com/foo/bar?&type=code)"
        out = render_keymap.render_note_text(text)
        self.assertIn('href="https://github.com/foo/bar?&amp;type=code"', out)
        self.assertIn('target="_blank"', out)
        self.assertIn('class="source-link"', out)
        self.assertIn('rel="noopener noreferrer"', out)
        self.assertIn(">code search</a>", out)

    def test_unsafe_link_and_script_stay_escaped(self):
        text = "[bad](javascript:alert(1)) <script>"
        out = render_keymap.render_note_text(text)
        self.assertNotIn("<a ", out)
        self.assertNotIn('href="javascript:', out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("[bad](javascript:alert(1))", out)


class RenderTelemetryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        keymap = (ROOT / "config" / "slicemk_ergodox.keymap").read_text()
        cls.page = render_keymap.build(
            keymap,
            {
                "commit": "working copy",
                "date": "",
                "repo_url": "",
                "source": "config/slicemk_ergodox.keymap",
                "panel": False,
            },
        )

    def test_keys_include_stable_telemetry_metadata(self):
        self.assertIn('data-position="1"', self.page)
        self.assertIn('data-side="left"', self.page)
        self.assertIn('data-layer="0"', self.page)
        self.assertIn('data-binding="&amp;kp ESC"', self.page)
        self.assertRegex(
            self.page,
            re.compile(
                r'data-behavior="(?:mt|tmt|df0|df1|dfk|df11)"'
                r'[^>]+data-dual="true"'
            ),
        )
        self.assertRegex(
            self.page,
            re.compile(
                r'data-target-layer="\d+"[^>]+data-target-gesture="hold"'
            ),
        )
        self.assertRegex(
            self.page,
            re.compile(
                r'data-target-layer="\d+"[^>]+data-target-gesture="press"'
            ),
        )
        self.assertNotIn('data-target-gesture="single"', self.page)

    def test_page_includes_trackers_and_shared_gesture_menu(self):
        self.assertEqual(self.page.count('class="keypress-buffer"'), 4)
        self.assertEqual(self.page.count('class="keypress-sequence"'), 4)
        self.assertEqual(self.page.count('class="keypress-results"'), 4)
        self.assertEqual(self.page.count('id="gesture-menu"'), 1)
        self.assertNotIn('data-gesture="single"', self.page)
        for gesture in ("press", "double", "hold", "tap-hold"):
            self.assertIn(f'data-gesture="{gesture}"', self.page)

    def test_telemetry_controller_is_inlined(self):
        self.assertIn("ergodox-keymap-tour-events-v1", self.page)
        self.assertIn("button.key[data-position]", self.page)
        self.assertEqual(self.page.count('class="keypress-copy-sequence"'), 4)
        self.assertEqual(self.page.count('class="keypress-copy-prompt"'), 4)
        self.assertIn('aria-label="Copy key sequence"', self.page)
        self.assertIn('aria-label="Copy reconfiguration prompt"', self.page)
        self.assertNotIn(".keypress-export", self.page)
        self.assertNotIn(">Export<", self.page)
        self.assertIn(".keypress-clear", self.page)
        self.assertIn("location.hash", self.page)
        self.assertIn("sequenceToken", self.page)
        self.assertIn("resultToken", self.page)
        self.assertIn("buildPrompt", self.page)
        self.assertIn("navigator.clipboard.writeText", self.page)
        self.assertIn("Key sequence:", self.page)
        self.assertIn("Resolved tour result:", self.page)
        self.assertIn("- Look up what ${result} does", self.page)
        self.assertNotIn("- Look up what ${sequence} does", self.page)
        self.assertIn("entry.position", self.page)
        self.assertIn("entry.gesture", self.page)
        self.assertIn("entry.behavior === 'lm'", self.page)
        self.assertIn("behavior === 'mo'", self.page)
        self.assertIn("behavior === 'lm'", self.page)
        self.assertIn("function layersText()", self.page)
        self.assertIn("Layers: ${layers || '(none)'}", self.page)
        self.assertIn("entry.layerName !== layers.at(-1)", self.page)

    def test_clear_returns_to_base_layer(self):
        self.assertIn("location.hash = 'layer-0';", self.page)

    def test_page_includes_safe_source_link_markup(self):
        self.assertIn('class="source-link"', self.page)
        self.assertIn('rel="noopener noreferrer"', self.page)


class LayerAppNotesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keymap = (ROOT / "config" / "slicemk_ergodox.keymap").read_text()
        cls.page = render_keymap.build(
            cls.keymap,
            {
                "commit": "working copy",
                "date": "",
                "repo_url": "",
                "source": "config/slicemk_ergodox.keymap",
                "panel": False,
            },
        )

    def test_keymap_source_slugs_match_expected_catalog(self):
        found = extract_source_slugs(self.keymap)
        self.assertEqual(found, EXPECTED_SOURCE_SLUGS)

    def test_keymap_has_no_ghostty_shortcat_or_scoot_source_links(self):
        forbidden = ("ghostty-f5-reload", "ghostty-", "shortcat", "scoot")
        for slug in extract_source_slugs(self.keymap):
            lowered = slug.lower()
            for bad in forbidden:
                self.assertNotIn(bad, lowered, slug)

    def test_base_rendered_app_bindings_and_conflicts(self):
        notes = layer_notes_html(self.page, 0)
        self.assertIn("App bindings:", notes)
        self.assertIn("Conflicts:", notes)
        for slug in (
            "aerospace-directional-focus",
            "aerospace-directional-move",
            "aerospace-resize",
            "aerospace-focus-cycle",
            "zellij-mode-entry",
            "zellij-new-tab",
            "zellij-quick-pane-tab",
            "zellij-quick-resize",
            "zellij-mode-cycle",
        ):
            with self.subTest(slug=slug):
                self.assertIn(f"keymap-ref%3A+{slug}", notes)
        self.assertIn("focus cycle shadows Ghostty tab cycle", notes)
        self.assertIn("Cmd+H/J/K/L: Zellij directional pane focus", notes)
        self.assertIn("Cmd+/: Zellij current-mode keybinding help", notes)
        self.assertNotIn("shadows Zellij quick actions for Alt+H/J/K/L", notes)
        self.assertIn("shadows Zellij quick resize for Alt+-/=", notes)
        self.assertIn("zellij-alt-quick-actions", notes)
        self.assertIn("Meh+-/=", notes)
        self.assertIn("Meh+G/H/N/S/T: Zellij mode entry", notes)
        self.assertNotIn("Meh+G/H/N/O/P/S/T", notes)
        self.assertNotIn("workspace move shadows Zellij session/pane entry", notes)
        self.assertNotIn("Ghostty consumes Cmd+T", notes)

    def test_symb_rendered_zellij_tab_note_without_ghostty_conflict(self):
        notes = layer_notes_html(self.page, 1)
        self.assertIn("App bindings:", notes)
        self.assertNotIn("Conflicts:", notes)
        self.assertIn("zellij-quick-pane-tab", notes)
        self.assertIn("Cmd+Shift+[", notes)
        self.assertNotIn("Ghostty consumes", notes)
        self.assertNotIn("ghostty-f5-reload", notes)
        self.assertNotIn("F5:", notes)

    def test_navi_rendered_app_bindings_and_shortcat_scoot_without_links(self):
        notes = layer_notes_html(self.page, 2)
        self.assertIn("App bindings:", notes)
        for slug in (
            "aerospace-workspaces",
            "aerospace-layout-cycle",
            "aerospace-service-mode",
        ):
            with self.subTest(slug=slug):
                self.assertIn(f"keymap-ref%3A+{slug}", notes)
        self.assertIn("com.sproutcube.Shortcat", notes)
        self.assertIn("KeyboardShortcuts_toggleShortcat", notes)
        self.assertIn("com.mjrusso.Scoot", notes)
        self.assertIn("KeyboardShortcuts_useGridBasedNavigation", notes)
        for chunk in notes.split("</div>"):
            if "Shortcat" in chunk or "Scoot" in chunk:
                self.assertNotIn('class="source-link"', chunk, chunk)
                self.assertNotIn("keymap-ref%3A", chunk, chunk)

    def test_nav3_rendered_ghostty_behavior_without_source_links(self):
        notes = layer_notes_html(self.page, 3)
        self.assertIn("Ghostty behavior:", notes)
        self.assertNotIn("Conflicts:", notes)
        self.assertNotIn("App bindings:", notes)
        self.assertNotIn('class="source-link"', notes)
        self.assertIn("Cmd+Up/Down", notes)
        self.assertIn("Cmd+Left/Right", notes)
        self.assertIn("Alt+Left/Right", notes)
        self.assertIn("Cmd+Ctrl+F", notes)


class KeymapAppNotesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keymap = (ROOT / "config" / "slicemk_ergodox.keymap").read_text()

    def test_base_app_bindings_follow_physical_layout_and_caps_word(self):
        base = self.keymap.split("base_layer {", 1)[0]
        caps = base.rindex("extended_caps_word")
        apps = base.rindex("App bindings:")
        self.assertLess(caps, apps, "App bindings should follow caps-word note")

    def test_symb_has_no_ghostty_f5_app_note(self):
        symb = layer_desc(self.keymap, "SYMB")
        self.assertNotIn("ghostty-f5-reload", symb)
        self.assertNotIn("F5:", symb)
        self.assertIn("zellij-quick-pane-tab", symb)


if __name__ == "__main__":
    unittest.main()
