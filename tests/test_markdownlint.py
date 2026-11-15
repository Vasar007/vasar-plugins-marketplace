"""Runs markdownlint on every tracked .md file of the repository.

The rules are in .markdownlint.jsonc at the repository root. The test runs a
pinned markdownlint-cli through npx, so it needs Node.js 22 or later. If npx is
not found, the test skips. If the environment variable CI is true, it fails. If
markdownlint finds none of the files, it prints its help text and exits with 0.
The test then also skips, and it fails if CI is true. The Windows npx under WSL2
does this when the clone is in the Linux file system, because cmd.exe cannot
use that folder as its current folder.
"""
import shutil
import subprocess
import unittest

from support import REPO, tool_missing, tracked_markdown_files

MARKDOWNLINT = "markdownlint-cli@0.49.1"
# On Windows, npx is npx.cmd, and cmd.exe allows at most 8,191 characters in one command line.
MAX_FILES_LENGTH = 6000
# markdownlint-cli prints this to stdout, and exits with 0, when no argument names a file that it can find.
HELP_TEXT = "Usage: markdownlint"


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


def linted_nothing(result):
    """True if markdownlint found none of its files and printed its help text instead of a lint result."""
    return result.returncode == 0 and HELP_TEXT in result.stdout


class BatchesTests(unittest.TestCase):
    def test_batches_keep_every_file_in_order_and_stay_under_the_limit(self):
        files = [f"folder-{i:03}/{'x' * 60}.md" for i in range(300)]
        result = list(batches(files))
        self.assertGreater(len(result), 1)
        self.assertEqual([f for batch in result for f in batch], files)
        for batch in result:
            self.assertLessEqual(sum(len(f) + 1 for f in batch), MAX_FILES_LENGTH)


class LintedNothingTests(unittest.TestCase):
    def test_only_the_help_text_with_exit_0_means_that_nothing_was_linted(self):
        help_text = "Usage: markdownlint [options] [files|directories|globs...]\n"
        hit = "a.md:3:28 error MD038/no-space-in-code Spaces inside code span elements\n"
        self.assertTrue(linted_nothing(subprocess.CompletedProcess([], 0, help_text, "")))
        self.assertFalse(linted_nothing(subprocess.CompletedProcess([], 0, "", "")))
        self.assertFalse(linted_nothing(subprocess.CompletedProcess([], 1, "", hit)))
        self.assertFalse(linted_nothing(subprocess.CompletedProcess([], 1, help_text, "")))
        self.assertFalse(linted_nothing(subprocess.CompletedProcess([], 0, "", help_text)))


class MarkdownlintTest(unittest.TestCase):
    def setUp(self):
        self.npx = shutil.which("npx")
        if self.npx is None:
            tool_missing(self, "npx not found. Install Node.js 22 or later to run markdownlint.")

    def markdownlint(self, files):
        return subprocess.run([self.npx, "--yes", MARKDOWNLINT, "--config", ".markdownlint.jsonc", *files],
                              cwd=REPO, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=600)

    def test_a_missing_file_gives_the_help_text(self):
        result = self.markdownlint(["no-such-file.md"])
        self.assertTrue(linted_nothing(result), f"{MARKDOWNLINT} exited with {result.returncode}. Its output does not "
                                                f"hold {HELP_TEXT!r}:\n{result.stdout}{result.stderr}")

    def test_no_warnings(self):
        failures = []
        for batch in batches(tracked_markdown_files()):
            result = self.markdownlint(batch)
            if linted_nothing(result):
                tool_missing(self, f"{MARKDOWNLINT} found none of the files and printed its help text, so it linted "
                                   f"nothing. One known cause is the Windows npx under WSL2, when the clone is in "
                                   f"the Linux file system: cmd.exe cannot use that folder as its current folder. "
                                   f"In that case, install Node.js 22 or later in Linux. npx: {self.npx}\n"
                                   f"{result.stderr}")
            if result.returncode != 0:
                failures.append(f"{MARKDOWNLINT} exited with {result.returncode}:\n{result.stdout}{result.stderr}")
        if failures:
            self.fail("\n".join(failures))


if __name__ == "__main__":
    unittest.main()
