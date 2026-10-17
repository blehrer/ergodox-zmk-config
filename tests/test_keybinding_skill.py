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

QUOTED_SEARCH_EXAMPLE = (
    "https://github.com/blehrer/dotfiles/search?"
    "q=%22keymap-ref%3A+zellij-mode-cycle%22&type=code"
)

STOP_AND_ASK_MARKERS = (
    "## Stop and ask",
    "(none)",
    "validation failures",
    "unrelated files unchanged",
    "marker ID already",
    "default binding cannot",
    "Conflict resolution requires",
)


class KeybindingSkillTest(unittest.TestCase):
    def test_skill_exists_and_includes_workflow_markers(self):
        text = SKILL.read_text()
        for snippet in REQUIRED_SNIPPETS:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)

    def test_skill_documents_stop_and_ask_conditions(self):
        text = SKILL.read_text()
        for snippet in STOP_AND_ASK_MARKERS:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)

    def test_skill_uses_quoted_github_code_search_urls(self):
        text = SKILL.read_text()
        self.assertIn(QUOTED_SEARCH_EXAMPLE, text)
        self.assertIn("%22keymap-ref%3A+", text)

    def test_skill_verify_uses_targeted_apply_and_full_unittest_discovery(self):
        text = SKILL.read_text()
        self.assertIn("chezmoi apply <target>", text)
        self.assertIn("python3 -m unittest discover -s tests", text)

    def test_skill_does_not_disable_model_invocation(self):
        text = SKILL.read_text()
        self.assertNotIn("disable-model-invocation: true", text)


if __name__ == "__main__":
    unittest.main()
