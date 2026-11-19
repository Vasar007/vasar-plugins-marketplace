"""Tests for the text of the model ladder: Opus at medium effort first, then more effort, then Fable.

The section "Model selection" of the skill subagent-orchestration owns the ladder. Fable is a step of the ladder,
not an exception. These tests fail if a file of a plugin keeps the old rule, for example after a merge.
"""
import unittest

from support import REPO

OLD_RULES = (
    "Fable is for exceptional cases only",
    "Exceptional cases only",
    "| Use Opus, and name the",
    "the Fable-eligible step",
    "Default. The executor for coding work",
    "pass the level that the task needs",
)


class ModelLadderTextTests(unittest.TestCase):
    def test_no_plugin_file_keeps_the_old_fable_rule(self):
        files = [p for base in ("essentials", "dotnet", "knowledge") for p in (REPO / base).rglob("*.md")]
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding="utf-8")
            for rule in OLD_RULES:
                with self.subTest(path=path.relative_to(REPO).as_posix(), rule=rule):
                    self.assertNotIn(rule, text)


if __name__ == "__main__":
    unittest.main()
