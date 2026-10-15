"""Runs markdownlint on every tracked .md file of the repository.

The rules are in .markdownlint.jsonc at the repository root. The test runs a
pinned markdownlint-cli through npx, so it needs Node.js 22 or later. If npx is
not found, the test skips. In CI it fails.
"""
import shutil
import subprocess
import unittest

from support import REPO, tool_missing, tracked_markdown_files

MARKDOWNLINT = "markdownlint-cli@0.49.1"
# On Windows, npx is npx.cmd, and cmd.exe allows at most 8,191 characters in one command line.
MAX_FILES_LENGTH = 6000


def batches(files):
    """Split the file list into batches, each with a total length of at most MAX_FILES_LENGTH."""
    batch, length = [], 0
    for file in files:
        if batch and length + len(file) + 1 > MAX_FILES_LENGTH:
            yield batch
            batch, length = [], 0
        batch.append(file)
        length += len(file) + 1
    if batch:
        yield batch


class BatchesTests(unittest.TestCase):
    def test_batches_keep_every_file_in_order_and_stay_under_the_limit(self):
        files = [f"folder-{i:03}/{'x' * 60}.md" for i in range(300)]
        result = list(batches(files))
        self.assertGreater(len(result), 1)
        self.assertEqual([f for batch in result for f in batch], files)
        for batch in result:
            self.assertLessEqual(sum(len(f) + 1 for f in batch), MAX_FILES_LENGTH)


class MarkdownlintTest(unittest.TestCase):
    def test_no_warnings(self):
        npx = shutil.which("npx")
        if npx is None:
            tool_missing(self, "npx not found. Install Node.js 22 or later to run markdownlint.")
        failures = []
        for batch in batches(tracked_markdown_files()):
            result = subprocess.run([npx, "--yes", MARKDOWNLINT, "--config", ".markdownlint.jsonc", *batch],
                                    cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=600)
            if result.returncode != 0:
                failures.append(f"{MARKDOWNLINT} exited with {result.returncode}:\n{result.stdout}{result.stderr}")
        if failures:
            self.fail("\n".join(failures))


if __name__ == "__main__":
    unittest.main()
