import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "keybinding-workflow" / "SKILL.md"

REQUIRED_SNIPPETS = (
    "name: keybinding-workflow",
    "Key sequence:",
    "Layers:",
    "Resolved tour result:",
    "chezmoi source-path",
    "App bindings:",
    "keymap-ref:",
    "github.com/blehrer/dotfiles/search",
)


class KeybindingSkillTest(unittest.TestCase):
    def test_skill_exists_and_includes_workflow_markers(self):
        text = SKILL.read_text()
        for snippet in REQUIRED_SNIPPETS:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)

    def test_skill_does_not_disable_model_invocation(self):
        text = SKILL.read_text()
        self.assertNotIn("disable-model-invocation: true", text)


if __name__ == "__main__":
    unittest.main()
