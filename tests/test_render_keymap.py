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


class RenderNoteTextTest(unittest.TestCase):
    def test_https_github_link_escapes_ampersand_in_href(self):
        text = "[code search](https://github.com/foo/bar?&type=code)"
        out = render_keymap.render_note_text(text)
        self.assertIn('href="https://github.com/foo/bar?&amp;type=code"', out)
        self.assertIn('target="_blank"', out)
        self.assertIn('rel="noopener"', out)
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

    def test_page_includes_app_bindings_in_layer_notes(self):
        self.assertIn("App bindings:", self.page)
        self.assertIn("Meh + Page Up: Zellij previous mode.", self.page)
        self.assertIn("Meh + Page Down: Zellij next mode.", self.page)
        self.assertIn("F5: Reload Ghostty config.", self.page)
        self.assertIn("keymap-ref%3A+zellij-mode-cycle", self.page)
        self.assertIn("keymap-ref%3A+ghostty-f5-reload", self.page)


if __name__ == "__main__":
    unittest.main()
