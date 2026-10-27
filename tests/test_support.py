"""Checks the helpers that the lint tests share."""
import subprocess
import unittest

from support import REPO, VENDORED, tracked_markdown_files, without_vendored


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


if __name__ == "__main__":
    unittest.main()
