"""Runs `claude plugin validate` and `claude plugin details` on the marketplace and on each plugin.

Each claude call gets an empty, temporary configuration folder and none of the known sign-in variables.
So it needs no sign-in, loads no installed plugin, and gets the offline token estimate of `claude plugin details`.
A Claude Code cloud session can still sign in through its token file. Then the budget test fails, and it does not hide an overrun.
If the claude command is not found, the tests skip. In CI they fail.
"""
import json
import math
import os
import re
import shutil
import unittest
from unittest import mock

from support import REPO, tool_missing
from testkit import ScratchCase, clean_env, run

PLUGIN_GLOB = "*/*/.claude-plugin/plugin.json"
# The most always-on tokens that `claude plugin details` may report for each plugin in a signed-in session.
# The always-on cost is the names and descriptions that every session loads.
LISTING_BUDGET = {
    "dev-essentials": 4785,
    "doc-styles": 191,
    "dotnet-backend-dev": 1875,
    "kb": 180,
}
# With no sign-in, `claude plugin details` reports an offline estimate (characters / 4), not the API count.
# On 2026-11-09 (Claude Code 2.1.310), the signed-in count was at most 1.48 times the estimate.
# A new default model can change the ratio. The kind of text changes it too: code and paths need more tokens for each character.
# The factor 1.5 was measured only on the current budgets. Measure the ratio again for a much smaller new budget.
SIGNED_IN_RATIO = 1.5
# With one of these variables, claude signs in or uses a cloud provider, and the count comes from the API.
SIGN_IN_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
    "CLAUDE_CODE_SESSION_ACCESS_TOKEN",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
    "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_VERTEX",
)
ALWAYS_ON = re.compile(r"^\s*Always-on:\s+(?:~|<\s*)?([\d,]+)\s+tok", re.MULTILINE)


def plugin_roots():
    return sorted(path.parent.parent for path in REPO.glob(PLUGIN_GLOB))


def plugin_name(root):
    return json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"]


def always_on_tokens(text):
    """The always-on token count in the output of `claude plugin details`. None if the output has none."""
    match = ALWAYS_ON.search(text)
    return int(match.group(1).replace(",", "")) if match else None


def signed_in_tokens(estimate):
    """The always-on tokens that a signed-in session can count for an offline estimate, rounded up."""
    return math.ceil(estimate * SIGNED_IN_RATIO)


def claude_env(config):
    """The environment of a claude call: the configuration folder, no auto-update, and no sign-in variables."""
    return clean_env(SIGN_IN_VARIABLES, CLAUDE_CONFIG_DIR=config, DISABLE_AUTOUPDATER="1")


class AlwaysOnTokensTests(unittest.TestCase):
    def test_reads_the_projected_cost_line(self):
        text = "Projected token cost\n  Always-on:   ~2,770 tok   added to every session\n"
        self.assertEqual(always_on_tokens(text), 2770)
        self.assertEqual(always_on_tokens("  Always-on:   < 20 tok   added to every session\n"), 20)
        self.assertIsNone(always_on_tokens("Plugin \"x\" not found.\n"))


class SignedInTokensTests(unittest.TestCase):
    def test_scales_the_estimate_and_rounds_up(self):
        self.assertEqual(signed_in_tokens(110), 165)
        self.assertEqual(signed_in_tokens(127), 191)
        self.assertEqual(signed_in_tokens(128), 192)


class ClaudeEnvTests(unittest.TestCase):
    def test_drops_the_sign_in_variables(self):
        with mock.patch.dict(os.environ, {**dict.fromkeys(SIGN_IN_VARIABLES, "x"), "TEST_PLUGIN_CLI_KEEP": "kept"}):
            env = claude_env("config")
        self.assertEqual([key for key in SIGN_IN_VARIABLES if key in env], [])
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "config")
        self.assertEqual(env["DISABLE_AUTOUPDATER"], "1")
        self.assertEqual(env["TEST_PLUGIN_CLI_KEEP"], "kept")


class ClaudeCliCase(ScratchCase):
    def setUp(self):
        self.claude = shutil.which("claude")
        if self.claude is None:
            tool_missing(self, "claude not found. Install Claude Code to run claude plugin validate and details.")
        super().setUp()
        self.env = claude_env(str(self.tmp))

    def run_claude(self, *args):
        result = run([self.claude, *args], cwd=REPO, env=self.env, timeout=120)
        return result.returncode, result.stdout + result.stderr


class ValidateTests(ClaudeCliCase):
    def test_marketplace(self):
        code, output = self.run_claude("plugin", "validate", "--strict", ".")
        self.assertEqual(code, 0, output)

    def test_each_plugin(self):
        roots = plugin_roots()
        self.assertTrue(roots, f"No plugin manifest matches {PLUGIN_GLOB}.")
        for root in roots:
            with self.subTest(plugin=root.relative_to(REPO).as_posix()):
                code, output = self.run_claude("plugin", "validate", "--strict", root)
                self.assertEqual(code, 0, output)


class ListingBudgetTests(ClaudeCliCase):
    def test_always_on_cost_stays_in_the_budget(self):
        names = {plugin_name(root): root for root in plugin_roots()}
        self.assertEqual(sorted(LISTING_BUDGET), sorted(names),
                         "Each plugin needs one entry in LISTING_BUDGET, and each entry needs a plugin.")
        for name, root in names.items():
            with self.subTest(plugin=name):
                code, output = self.run_claude("--plugin-dir", root, "plugin", "details", name)
                self.assertEqual(code, 0, output)
                estimate = always_on_tokens(output)
                self.assertIsNotNone(estimate, f"No 'Always-on:' line in the output:\n{output}")
                tokens = signed_in_tokens(estimate)
                self.assertLessEqual(tokens, LISTING_BUDGET[name],
                                     f"{name} adds about {tokens} always-on tokens to a signed-in session (the offline "
                                     f"estimate {estimate} times {SIGNED_IN_RATIO}), over its budget of "
                                     f"{LISTING_BUDGET[name]}. Shorten the descriptions that the table below shows "
                                     f"as the largest. Raise the budget only for a new component.\n{output}")


if __name__ == "__main__":
    unittest.main()
