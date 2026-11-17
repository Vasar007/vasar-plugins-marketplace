"""Tests for the text of the review-loop skill: the fix plan of the reviewer and the choice of the fixer.

The skill text decides who plans and who applies each fix. These tests pin the sentences that a later
edit must not lose: the plan line of the Full format, the plan dispatch only for a finding with no plan,
and the fixer subagent for a large fix set or a fixer flag.
"""
import re
import unittest

from support import REPO

SKILL_DIR = REPO / "essentials/dev-essentials/skills/review-loop"


def read(name):
    return (SKILL_DIR / name).read_text(encoding="utf-8")


def section(text, start, end):
    """The text from the first line that holds start up to the next line that holds end."""
    head = text.index(start)
    return text[head:text.index(end, head)]


class FixPlanTextTests(unittest.TestCase):
    def test_the_full_format_asks_for_a_fix_plan_in_each_finding(self):
        full = section(read("references/reviewer-briefs.md"), "## Full format", "## Conclusion")
        self.assertIn("- **Fix plan:**", full)

    def test_the_common_rules_ask_for_a_fix_plan(self):
        rules = section(read("references/reviewer-briefs.md"), "## Common Rules", "## Full format")
        self.assertIn("**Fix plan for each finding**", rules)

    def test_step_5a_dispatches_a_plan_only_for_a_finding_with_no_usable_plan(self):
        step = section(read("SKILL.md"), "**Step 5a:", "**Step 5b:")
        self.assertIn("no separate dispatch plans the fixes", step)
        self.assertIn("runs only for the findings that have no usable plan", step)
        self.assertIn("`--reviewer-model`", step)

    def test_audit_team_and_orchestrated_mode_keep_the_plan_dispatch(self):
        self.assertIn("plan dispatch on `--reviewer-model`", read("references/audit-team-adapter.md"))
        self.assertIn("step 5a plans the fixes with one plan dispatch", read("references/orchestrated-review.md"))


class FixerChoiceTextTests(unittest.TestCase):
    def test_step_5b_names_the_tests_of_rule_1_and_keeps_the_subagent(self):
        step = section(read("SKILL.md"), "**Step 5b:", "The rules that the fixer must follow:")
        self.assertIn("Rule 1 of `dev-essentials:subagent-orchestration`", step)
        self.assertIn("dispatch a fixer subagent", step)
        for flag in ("`--fixer`", "`--fixer-model`", "`--fixer-effort`"):
            with self.subTest(flag=flag):
                self.assertIn(flag, step)
        self.assertIn("references/verify-fix-discipline.md", step)

    def test_step_5b_names_no_count_of_findings_or_files(self):
        step = section(read("SKILL.md"), "**Step 5b:", "The rules that the fixer must follow:")
        self.assertNotRegex(step, r"\b\d+\s+(?:findings?|files?|edits?|lines?|fixes)\b")

    def test_the_brief_format_names_the_fixer(self):
        self.assertIn("Fixer: <orchestrator | subagent>", read("references/output-formats.md"))


if __name__ == "__main__":
    unittest.main()
