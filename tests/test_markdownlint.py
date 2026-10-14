"""Runs markdownlint on the .md files of the plugins.

The rules are in .markdownlint.jsonc at the repository root. The test runs a
pinned markdownlint-cli through npx, so it needs Node.js 22 or later. If npx is
not found, the test skips. In CI it fails.
"""
import shutil
import subprocess
import unittest

from support import PLUGIN_DIRS, REPO, tool_missing

MARKDOWNLINT = "markdownlint-cli@0.49.1"


class MarkdownlintTest(unittest.TestCase):
    def test_no_warnings(self):
        npx = shutil.which("npx")
        if npx is None:
            tool_missing(self, "npx not found. Install Node.js 22 or later to run markdownlint.")
        result = subprocess.run([npx, "--yes", MARKDOWNLINT, "--config", ".markdownlint.jsonc", *PLUGIN_DIRS],
                                cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=600)
        if result.returncode != 0:
            self.fail(f"{MARKDOWNLINT} exited with {result.returncode}:\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
