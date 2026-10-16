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
        self.assertIn(".keypress-export", self.page)
        self.assertIn(".keypress-clear", self.page)
        self.assertIn("location.hash", self.page)
        self.assertIn("sequenceToken", self.page)
        self.assertIn("resultToken", self.page)
        self.assertIn("entry.position", self.page)
        self.assertIn("entry.gesture", self.page)
        self.assertIn("entry.behavior === 'lm'", self.page)
        self.assertIn("behavior === 'mo'", self.page)
        self.assertIn("behavior === 'lm'", self.page)

    def test_clear_returns_to_base_layer(self):
        self.assertIn("location.hash = 'layer-0';", self.page)


if __name__ == "__main__":
    unittest.main()
