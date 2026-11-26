"""Tests for the gh rule: Rule 5 of github-mcp-conventions and the units that point at it.

The rule allows the gh CLI only when no GitHub MCP tool can make a call. These tests fail if a part of the rule
leaves Rule 5, or if a unit keeps the old ban.
"""
import re
import unittest

from support import REPO

DEV = REPO / "essentials" / "dev-essentials"
CONVENTIONS = DEV / "skills" / "github-mcp-conventions" / "SKILL.md"
ORCHESTRATION = DEV / "skills" / "subagent-orchestration" / "SKILL.md"
MERGE_PR = DEV / "skills" / "merge-pr" / "SKILL.md"

OLD_RULES = (
    "No REST/`gh`-CLI fallback",
    "Never fall back to the `gh` CLI or REST",
    "no fallback to REST or to the `gh` CLI",
    "Never silently fall back to REST APIs or CLI tools",
    "names the one exception, a PR that `promote-conventions` creates",
    "a token with no access to the check runs makes a read fail",
    "The rule to use only the GitHub MCP tools",
    "not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires",
)

RULE_5_PARTS = (
    "Try the GitHub MCP tool first.",
    "No GitHub MCP tool has the call, or a field that the step needs.",
    "A tool that the session lists with only its name counts too",
    "The MCP call fails, and it fails again after one retry.",
    "If you can fix the call, fix it, and stay with MCP.",
    "After a failed MCP write, first read whether the write landed (Rule 4).",
    "A case holds for that one call. Make the next call with MCP.",
    "list the issues and look for the title before you call again",
    "Name each `gh` call and its reason in the report",
    "A `gh` call keeps each approval gate of the workflow",
    "A failed `merge_pull_request` call never goes through `gh`.",
    "A slow MCP call, or a shorter `gh` command, is never a reason to use `gh`.",
    "Do not try `curl`, a REST call outside `gh`, or a script.",
    "A missing server is not case 1.",
    "A skill that gives its own stop or its own `gh` step wins over this rule.",
    "A `gh` command that the user or the project instructions name is not a fallback.",
    '`method: "get_check_runs"`', "`gh release create`", "`issue_write`", "`create_pull_request`", "blocked-by", "`search_issues`",
)


def plugin_files():
    """The Markdown files of the plugins, as test_model_ladder_text.py reads them."""
    return [p for base in ("essentials", "dotnet", "knowledge") for p in (REPO / base).rglob("*.md")]


def section(text, start, end=r"^## "):
    """The text from the line that starts with start to the next line that matches end."""
    found = re.search(rf"^{re.escape(start)}.*?(?={end})", text, re.S | re.M)
    return found.group(0) if found else None


class GhFallbackTextTests(unittest.TestCase):
    def test_no_plugin_file_keeps_the_old_gh_ban(self):
        files = plugin_files()
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding="utf-8")
            for rule in OLD_RULES:
                with self.subTest(path=path.relative_to(REPO).as_posix(), rule=rule):
                    self.assertNotIn(rule, text)

    def test_rule_5_holds_each_part_of_the_rule(self):
        rule = section(CONVENTIONS.read_text(encoding="utf-8"), "## Rule 5 — ")
        self.assertIsNotNone(rule, "github-mcp-conventions has no Rule 5.")
        for part in RULE_5_PARTS:
            with self.subTest(part=part):
                self.assertIn(part, rule)

    def test_rule_4_of_subagent_orchestration_points_at_the_two_cases(self):
        rule = section(ORCHESTRATION.read_text(encoding="utf-8"), "## Rule 4 — ")
        self.assertIsNotNone(rule, "subagent-orchestration has no Rule 4.")
        for part in ("Rule 5 of `dev-essentials:github-mcp-conventions`",
                     "no MCP tool has the call or a field that it needs",
                     "the call fails again after a retry",
                     "A missing server is not one of these cases.",
                     "A subagent names each `gh` call and its reason in its report.",
                     "A skill that names its own `gh` step follows that step.",
                     "The main agent repairs a missing server, because the user sees the MCP errors there."):
            with self.subTest(part=part):
                self.assertIn(part, rule)

    def test_the_merge_gate_reads_the_check_runs_with_gh_after_a_failed_mcp_read(self):
        text = MERGE_PR.read_text(encoding="utf-8")
        gate = section(text, "## Step 2: The gate", r"^## Step 3")
        self.assertIsNotNone(gate)
        self.assertIn('gh api --paginate "repos/<owner>/<repo>/commits/<head.sha>/check-runs', gate)
        self.assertIn("If the MCP read of the check runs fails again after one retry", gate)
        self.assertIn("Rule 5 of `dev-essentials:github-mcp-conventions` allows this call.", gate)
        self.assertIn("If the MCP read of the combined status fails again after one retry, read it from", gate)
        self.assertIn("For example, the MCP call and the `gh` call of item 1 can both fail. Then the read fails.", gate)
        # The gh read is a way to read the checks. It must not become a way to approve the merge.
        approval = section(text, "## Approval", r"^## Step 1")
        self.assertIsNotNone(approval)
        self.assertNotRegex(approval, r"\bgh\b")

    def test_the_merge_reads_the_base_checks_with_gh_and_reports_each_gh_call(self):
        text = MERGE_PR.read_text(encoding="utf-8")
        after = section(text, "## Step 4", r"^## Never")
        self.assertIsNotNone(after)
        self.assertIn('use `gh api --paginate "repos/<owner>/<repo>/commits/<merge commit SHA>/check-runs?per_page=100"`', after)
        self.assertIn("If neither MCP nor `gh` can read them, say in the report that nobody read these checks.", after)
        report = section(text, "## Report", r"\Z")
        self.assertIsNotNone(report)
        self.assertIn("Name each `gh` call and its reason.", report)

    def test_the_description_limits_gh_to_two_cases_and_one_call(self):
        text = CONVENTIONS.read_text(encoding="utf-8")
        found = re.search(r'^description: "(.*)"$', text, re.M)
        self.assertIsNotNone(found, "The description must be one double-quoted line.")
        self.assertIn("If no MCP tool has the call, or the call fails twice, use `gh` for that call only.", found.group(1))


if __name__ == "__main__":
    unittest.main()
