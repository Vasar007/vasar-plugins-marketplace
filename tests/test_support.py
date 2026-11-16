"""Checks the helpers that the lint tests share."""
import subprocess
import sys
import unittest

from support import REPO, VENDORED, run_with_open_stdin, tracked_markdown_files, without_vendored


class WithoutVendoredTests(unittest.TestCase):
    def test_drops_the_paths_under_a_vendored_folder_only(self):
        vendored = next(iter(VENDORED))
        paths = [vendored + "skills/x/SKILL.md", vendored[:-1] + "-other/a.md", "README.md"]
        self.assertEqual(without_vendored(paths), paths[1:])


class VendoredFoldersTests(unittest.TestCase):
    def test_each_vendored_folder_has_tracked_files_and_a_reason(self):
        for folder, reason in VENDORED.items():
            with self.subTest(folder=folder):
                self.assertTrue(reason)
                out = subprocess.run(["git", "-C", str(REPO), "ls-files", "--", folder],
                                     capture_output=True, text=True, check=True).stdout
                self.assertTrue(out.strip(), f"{folder} has no tracked file. Remove it from VENDORED.")

    def test_tracked_markdown_files_skip_the_vendored_folders(self):
        for path in tracked_markdown_files():
            self.assertFalse(path.startswith(tuple(VENDORED)), path)


class RunWithOpenStdinTests(unittest.TestCase):
    def test_returns_the_result_of_a_command_that_reads_no_input(self):
        result = run_with_open_stdin([sys.executable, "-c", "import sys; print('out'); sys.exit(3)"])
        self.assertEqual((result[0], result[1].strip(), result[2]), (3, "out", ""))

    def test_returns_none_for_a_command_that_waits_for_input(self):
        result = run_with_open_stdin([sys.executable, "-c", "import sys; sys.stdin.read()"], timeout=2)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
