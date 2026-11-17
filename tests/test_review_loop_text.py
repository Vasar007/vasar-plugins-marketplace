"""Tests for the text of the review-loop skill: the fix plan of the reviewer and the choice of the fixer.

The skill text decides who plans and who applies each fix. These tests pin the sentences that a later
edit must not lose: the plan line of the Full format, the plan dispatch only for a finding with no plan,
and the fixer subagent for the context test or a fixer flag.
"""
import re
import unittest

from support import REPO

SKILL_DIR = REPO / "essentials/dev-essentials/skills/review-loop"
ORCHESTRATION = REPO / "essentials/dev-essentials/skills/subagent-orchestration/SKILL.md"
COUNT = re.compile(
    r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:\w+\s+)?"
    r"(?:findings?|files?|edits?|lines?|fixes)\b",
    re.IGNORECASE,
)
SESSION_SIZE = (
    r"(?i)\b(?:long|short|fresh|new)\s+session|\bsession is (?:long|short|large|small|new)|size of the session"
)
FIX_SET_SIZE = r"(?i)\b(?:small|large|big)\s+(?:fix sets?|one)\b|\bfix sets? (?:is|are) (?:small|large|big)\b"


def read(name):
    return (SKILL_DIR / name).read_text(encoding="utf-8")


def section(text, start, end):
    """The text from the first match of start up to the next match of end."""
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

    def test_step_5a_names_the_regression_fix_as_a_case_with_no_plan(self):
        step = section(read("SKILL.md"), "**Step 5a:", "**Step 5b:")
        self.assertIn("The fix is the regression fix after the failure check of Phase 6.", step)

    def test_audit_team_and_orchestrated_mode_keep_the_plan_dispatch(self):
        self.assertIn("plan dispatch on `--reviewer-model`", read("references/audit-team-adapter.md"))
        self.assertIn("step 5a plans the fixes with one plan dispatch", read("references/orchestrated-review.md"))
        self.assertIn("from the collated and checked findings, with no Fix plan line.", read("references/orchestrated-review.md"))


class FixerChoiceTextTests(unittest.TestCase):
    def test_step_5b_names_the_tests_of_rule_1_and_keeps_the_subagent(self):
        step = section(read("SKILL.md"), "**Step 5b:", "The rules that the fixer must follow:")
        self.assertIn("Rule 1 of `dev-essentials:subagent-orchestration`", step)
        self.assertIn("dispatch a fixer subagent", step)
        for flag in ("`--fixer`", "`--fixer-model`", "`--fixer-effort`"):
            with self.subTest(flag=flag):
                self.assertIn(flag, step)
        self.assertIn("references/verify-fix-discipline.md", step)

    def test_step_5b_keeps_the_orchestrator_path_and_the_flag_rule(self):
        step = section(read("SKILL.md"), "**Step 5b:", "The rules that the fixer must follow:")
        self.assertIn("Else the orchestrator applies the fixes itself.", step)
        self.assertIn(
            "If the reads and the edits of the fix set put many files into the main context, dispatch a fixer subagent.",
            step,
        )
        self.assertIn("dispatch the fixer subagent for every fix set", step)
        self.assertIn("In the orchestrator, read", step)

    def test_step_5b_decides_from_the_fix_plans_and_not_from_the_session(self):
        step = section(read("SKILL.md"), "**Step 5b:", "The rules that the fixer must follow:")
        self.assertNotIn("the session already read", step)
        self.assertIn("Decide from the fix plans, not from the files that this session already holds.", step)
        self.assertEqual(step.count("this session"), 1)

    def test_the_check_scope_lets_the_orchestrator_test_findings_when_it_is_the_fixer(self):
        scope = section(read("SKILL.md"), "- Check scope:", "- Reporting:")
        self.assertIn("If the orchestrator is the fixer (Phase 5, step 5b), it reads the cited code and tests each finding itself.", scope)
        self.assertIn("to test the verdict of a fixer subagent again.", scope)

    def test_the_choice_of_the_fixer_names_no_count_and_no_session_size(self):
        default = section(read("SKILL.md"), "## Default configuration", "## Autonomy")
        fixer_row = section(read("references/parameters.md"), "| `--fixer <id>`", "\n")
        step = section(read("SKILL.md"), "**Step 5b:", "The rules that the fixer must follow:")
        intro = section(read("SKILL.md"), "# Review Loop", "## Done test")
        playbook = section(read("references/verify-fix-discipline.md"), "**Read this file", "## Contents")
        texts = (
            ("intro", intro),
            ("step 5b", step),
            ("default configuration", default),
            ("--fixer row", fixer_row),
            ("playbook", playbook),
        )
        for name, text in texts:
            with self.subTest(text=name):
                self.assertNotRegex(text, COUNT)
                self.assertNotRegex(text, SESSION_SIZE)
                self.assertNotRegex(text, FIX_SET_SIZE)

    def test_the_intro_and_the_default_configuration_point_at_step_5b(self):
        intro = section(read("SKILL.md"), "# Review Loop", "## Done test")
        default = section(read("SKILL.md"), "## Default configuration", "## Autonomy")
        self.assertIn("If step 5b chooses a fixer subagent, it also dispatches that subagent.", intro)
        self.assertIn("The orchestrator applies the fixes, unless Phase 5, step 5b sends the fix set", default)
        for name, text in (("intro", intro), ("default configuration", default)):
            with self.subTest(text=name):
                self.assertNotIn("context test", text)

    def test_rule_1_of_subagent_orchestration_names_no_fix_set_size(self):
        rule = section(ORCHESTRATION.read_text(encoding="utf-8"), "**A phase that itself orchestrates", "\n")
        self.assertIn("and it can dispatch its own fixer subagent.", rule)
        self.assertNotRegex(rule, FIX_SET_SIZE)

    def test_the_fixer_rows_keep_the_backticks_of_the_fields(self):
        params = read("references/parameters.md")
        self.assertIn("passed in the `model` field of its `Agent` call.", params)
        self.assertIn("passed in the `effort` field of its `Agent` call.", params)

    def test_the_brief_format_names_the_fixer(self):
        self.assertIn("Fixer: <orchestrator | subagent | none>", read("references/output-formats.md"))


AUDIT_TEAM = REPO / "essentials/dev-essentials/commands/audit-team.md"


class AuditTeamCountTextTests(unittest.TestCase):
    """The adapter keeps the five-role team of /audit-team, and the command keeps the meaning of an explicit count."""

    def test_the_adapter_always_passes_a_count_of_5(self):
        line = section(read("references/audit-team-adapter.md"), "- `[agent-count]`", "\n")
        self.assertIn("the value from `--audit-team-args`, or else `5`.", line)
        self.assertIn("This skill keeps the five-role team.", line)
        self.assertIn("must produce `/audit-team <path> 5 opus`", line)
        self.assertNotIn("the default of `/audit-team`", line)

    def test_the_spec_example_passes_the_fixed_count(self):
        example = read("examples/spec-review.md")
        self.assertIn("gets the fixed value `5` of the adapter", example)
        self.assertIn("`/audit-team openspec/changes/add-tenant-quotas/proposal.md 5 opus`", example)
        self.assertNotIn("the default of `/audit-team`", example)

    def test_the_command_keeps_the_team_route_for_an_explicit_count(self):
        command = AUDIT_TEAM.read_text(encoding="utf-8")
        self.assertIn("With a count, the run takes the team route. With no count, it takes the two-view route.", command)
        self.assertIn("one agent for each of the first N roles, in the order of the table.", command)
        self.assertIn("If the second argument is not a whole number, it is the model, and the run takes the two-view "
                      "route.", command)
        self.assertNotIn("default: 5", command)


if __name__ == "__main__":
    unittest.main()
