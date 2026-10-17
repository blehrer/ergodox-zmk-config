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

EXTERNAL_PREFERENCE_MARKERS = (
    "externally managed",
    "defaults read",
    "preference domain",
    "do not add a `keymap-ref:`",
    "GitHub source link",
    "cannot be read",
    "differs from the documented chord",
)

EXTERNAL_PREFERENCE_DEFAULTS_EXAMPLES = (
    "defaults read com.sproutcube.Shortcat KeyboardShortcuts_toggleShortcat",
    "defaults read com.mjrusso.Scoot KeyboardShortcuts_useGridBasedNavigation",
)

GHOSTTY_CONFLICT_AUDIT_MARKERS = (
    "+list-keybinds",
    "effective merged",
    "outside chezmoi",
    "effective bindings count as conflicts",
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

    def test_skill_documents_external_preferences(self):
        text = SKILL.read_text()
        for snippet in EXTERNAL_PREFERENCE_MARKERS:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)
        for example in EXTERNAL_PREFERENCE_DEFAULTS_EXAMPLES:
            with self.subTest(example=example):
                self.assertIn(example, text)

    def test_skill_documents_ghostty_effective_binding_audit(self):
        text = SKILL.read_text()
        for snippet in GHOSTTY_CONFLICT_AUDIT_MARKERS:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, text)
        self.assertNotIn("+list-keybinds --default", text)
        self.assertNotIn("ghostty --default", text)


if __name__ == "__main__":
    unittest.main()
