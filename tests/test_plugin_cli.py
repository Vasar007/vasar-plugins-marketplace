"""Runs `claude plugin validate` and `claude plugin details` on the marketplace and on each plugin.

Each claude call gets an empty, temporary configuration folder, so it needs no sign-in and loads no installed plugin.
If the claude command is not found, the tests skip. In CI they fail.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from support import REPO, tool_missing

PLUGIN_GLOB = "*/*/.claude-plugin/plugin.json"
# The most always-on tokens that `claude plugin details` may report for each plugin.
# The always-on cost is the names and descriptions that every session loads.
LISTING_BUDGET = {
    "dev-essentials": 3100,
    "dotnet-backend-dev": 1250,
    "gop-pipeline": 550,
}
ALWAYS_ON = re.compile(r"^\s*Always-on:\s+(?:~|<\s*)?([\d,]+)\s+tok", re.MULTILINE)


def plugin_roots():
    return sorted(path.parent.parent for path in REPO.glob(PLUGIN_GLOB))


def plugin_name(root):
    return json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["name"]


def always_on_tokens(text):
    """The always-on token count in the output of `claude plugin details`. None if the output has none."""
    match = ALWAYS_ON.search(text)
    return int(match.group(1).replace(",", "")) if match else None


class AlwaysOnTokensTests(unittest.TestCase):
    def test_reads_the_projected_cost_line(self):
        text = "Projected token cost\n  Always-on:   ~2,770 tok   added to every session\n"
        self.assertEqual(always_on_tokens(text), 2770)
        self.assertEqual(always_on_tokens("  Always-on:   < 20 tok   added to every session\n"), 20)
        self.assertIsNone(always_on_tokens("Plugin \"x\" not found.\n"))


class ClaudeCliCase(unittest.TestCase):
    def setUp(self):
        self.claude = shutil.which("claude")
        if self.claude is None:
            tool_missing(self, "claude not found. Install Claude Code to run claude plugin validate and details.")
        config = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, config, True)
        self.env = {**os.environ, "CLAUDE_CONFIG_DIR": config, "DISABLE_AUTOUPDATER": "1"}

    def run_claude(self, *args):
        result = subprocess.run([self.claude, *map(str, args)], cwd=REPO, env=self.env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=120)
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
                tokens = always_on_tokens(output)
                self.assertIsNotNone(tokens, f"No 'Always-on:' line in the output:\n{output}")
                self.assertLessEqual(tokens, LISTING_BUDGET[name],
                                     f"{name} adds about {tokens} always-on tokens to every session, over its budget "
                                     f"of {LISTING_BUDGET[name]}. Shorten the descriptions that the table below shows "
                                     f"as the largest. Raise the budget only for a new component.\n{output}")


if __name__ == "__main__":
    unittest.main()
