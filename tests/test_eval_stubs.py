"""Reports when an eval stand-in is older than the plugin that is installed.

The stand-in tests/evals/stubs/simple-english is a copy of the
plugin simple-english. Its SOURCE.txt names the copied version. The test reads
the installed versions from plugins/cache/simple-english/simple-english/ in
CLAUDE_CONFIG_DIR (default ~/.claude). The test fails if one is newer. It skips
if none is installed, which is the case in CI.
"""
import os
import re
import unittest
from pathlib import Path

from support import REPO
from testkit import ScratchCase

STUB = REPO / "tests/evals/stubs/simple-english"
CACHE = Path("plugins/cache/simple-english/simple-english")
VERSION_LINE = re.compile(r"^Version:\s*(\d+)\.(\d+)\.(\d+)", re.MULTILINE)
VERSION_NAME = re.compile(r"\d+\.\d+\.\d+")


def dotted(version):
    return ".".join(map(str, version))


def newest_installed(config_dir):
    """The newest version folder in the plugin cache, as a tuple of integers, or None."""
    folder = Path(config_dir) / CACHE
    if not folder.is_dir():
        return None
    versions = [tuple(map(int, p.name.split("."))) for p in folder.iterdir()
                if p.is_dir() and VERSION_NAME.fullmatch(p.name)]
    return max(versions, default=None)


def check_drift(source_file, config_dir):
    """Returns ("ok" | "skip" | "fail", message)."""
    match = VERSION_LINE.search(Path(source_file).read_text(encoding="utf-8"))
    if match is None:
        return "fail", f"{source_file} has no line 'Version: X.Y.Z'. Add the version of the copied plugin."
    stub = tuple(map(int, match.groups()))
    installed = newest_installed(config_dir)
    if installed is None:
        return "skip", "simple-english is not installed, so the stand-in cannot be compared."
    if installed > stub:
        return "fail", (f"The stand-in is simple-english {dotted(stub)}, but simple-english {dotted(installed)} is installed. "
                        "Copy the plugin files again, keep the left-out list of SOURCE.txt, update SOURCE.txt, "
                        "and run the style-compare suites of doc-styles again.")
    return "ok", ""


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"


class StandInVersionTests(unittest.TestCase):
    def test_the_simple_english_stand_in_is_not_older_than_the_installed_plugin(self):
        status, message = check_drift(STUB / "SOURCE.txt", config_dir())
        if status == "skip":
            self.skipTest(message)
        self.assertEqual(status, "ok", message)


class CheckDriftTests(ScratchCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp
        self.source = self.root / "SOURCE.txt"
        self.source.write_text("Source: x\nVersion: 2.1.1 (MIT, see LICENSE)\n", encoding="utf-8")

    def install(self, *names):
        for name in names:
            (self.root / CACHE / name).mkdir(parents=True)

    def test_a_newer_installed_version_fails_and_names_both_versions(self):
        self.install("2.1.1", "2.10.0")
        status, message = check_drift(self.source, self.root)
        self.assertEqual(status, "fail")
        self.assertIn("2.1.1", message)
        self.assertIn("2.10.0", message)
        self.assertIn("SOURCE.txt", message)

    def test_an_equal_installed_version_passes(self):
        self.install("2.1.1")
        self.assertEqual(check_drift(self.source, self.root)[0], "ok")

    def test_an_older_installed_version_passes(self):
        self.install("2.0.9")
        self.assertEqual(check_drift(self.source, self.root)[0], "ok")

    def test_versions_compare_as_numbers_and_not_as_text(self):
        self.install("2.9.0")
        self.assertEqual(check_drift(self.source, self.root)[0], "fail")
        self.source.write_text("Version: 10.0.0\n", encoding="utf-8")
        self.assertEqual(check_drift(self.source, self.root)[0], "ok")

    def test_folder_names_that_are_not_versions_are_ignored(self):
        self.install("latest", "9.9", "2.1.1")
        self.assertEqual(check_drift(self.source, self.root)[0], "ok")

    def test_no_installed_copy_skips(self):
        status, message = check_drift(self.source, self.root)
        self.assertEqual(status, "skip")
        self.assertIn("not installed", message)

    def test_a_missing_version_line_fails_even_without_an_install(self):
        self.source.write_text("Source: x\n", encoding="utf-8")
        status, message = check_drift(self.source, self.root)
        self.assertEqual(status, "fail")
        self.assertIn("Version: X.Y.Z", message)


if __name__ == "__main__":
    unittest.main()
