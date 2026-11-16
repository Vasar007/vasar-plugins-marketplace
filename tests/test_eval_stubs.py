"""Reports when an eval stand-in is older than the plugin that is installed.

The stand-in tests/evals/stubs/simple-english is a copy of the
plugin simple-english. Its SOURCE.txt names the copied version. The test reads
the installed versions from plugins/cache/simple-english/simple-english/ in
CLAUDE_CONFIG_DIR (default ~/.claude). It also reads the synced copies, which
are the folders plugins/synced/*/simple-english and plugins/synced/*/simple-english~g<N>.
Their version is in .claude-plugin/plugin.json. The test fails if one is newer.
It skips if none is installed, which is the case in CI.
"""
import json
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
SYNCED = Path("plugins/synced")
SYNCED_NAME = re.compile(r"simple-english(~g\d+)?")


def dotted(version):
    return ".".join(map(str, version))


def synced_version(folder):
    """The version in the plugin.json of a synced copy, as a tuple of integers, or None."""
    try:
        manifest = json.loads((folder / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    text = manifest.get("version") if isinstance(manifest, dict) else None
    return tuple(map(int, text.split("."))) if isinstance(text, str) and VERSION_NAME.fullmatch(text) else None


def newest_installed(config_dir):
    """The newest version in the plugin cache and in the synced copies, as a tuple of integers, or None."""
    versions = []
    cache = Path(config_dir) / CACHE
    if cache.is_dir():
        versions += [tuple(map(int, p.name.split("."))) for p in cache.iterdir()
                     if p.is_dir() and VERSION_NAME.fullmatch(p.name)]
    synced = Path(config_dir) / SYNCED
    if synced.is_dir():
        versions += [v for p in synced.glob("*/simple-english*")
                     if p.is_dir() and SYNCED_NAME.fullmatch(p.name) and (v := synced_version(p))]
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

    def install_synced(self, name, version, group="abc_def"):
        manifest = self.root / SYNCED / group / name / ".claude-plugin/plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": "simple-english", "version": version}), encoding="utf-8")

    def test_a_newer_synced_copy_fails(self):
        self.install_synced("simple-english", "2.2.0")
        status, message = check_drift(self.source, self.root)
        self.assertEqual(status, "fail")
        self.assertIn("2.2.0", message)

    def test_an_equal_synced_copy_passes(self):
        self.install_synced("simple-english", "2.1.1")
        self.assertEqual(check_drift(self.source, self.root)[0], "ok")

    def test_a_synced_copy_with_a_g_suffix_counts(self):
        self.install_synced("simple-english~g2", "2.3.0")
        self.assertEqual(check_drift(self.source, self.root)[0], "fail")

    def test_a_synced_copy_with_no_readable_version_is_skipped(self):
        self.install_synced("simple-english", "latest")
        (self.root / SYNCED / "abc_def" / "simple-english~g2").mkdir()
        self.assertEqual(check_drift(self.source, self.root)[0], "skip")

    def test_a_synced_copy_whose_manifest_is_not_an_object_is_skipped(self):
        manifest = self.root / SYNCED / "abc_def" / "simple-english" / ".claude-plugin/plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("[]", encoding="utf-8")
        self.assertEqual(check_drift(self.source, self.root)[0], "skip")

    def test_a_synced_folder_of_another_plugin_is_ignored(self):
        self.install_synced("simple-english-extra", "9.0.0")
        self.install_synced("other-plugin", "9.0.0", group="ghi_jkl")
        self.assertEqual(check_drift(self.source, self.root)[0], "skip")

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
