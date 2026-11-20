"""Tests for tools/release.py.

Each test of section writes a small CHANGELOG.md and three plugin.json files into a temporary folder. Each
test of notes commits a CHANGELOG.md into a new git repository. The tests run the script as a child process.
The docstring of each test names the bug that makes it fail.
"""
import os
import shutil
import sys
import unittest
from unittest import mock

from support import REPO, tool_missing
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "tools" / "release.py"
URL = "https://example.com/owner/repo/compare/"
DEV = "essentials/dev-essentials"
DOTNET = "dotnet/dotnet-backend-dev"
KB = "knowledge/kb"
INTRO = "# Changelog\n\nThe intro.\n\n## [Unreleased]\n\n"


def section(plugins, release, bullets=("the change",)):
    lines = "".join(f"- {bullet}\n" for bullet in bullets)
    return f"## {plugins} in release [{release}] - 2026-11-20\n\nThe summary of {release}.\n\n### Changed in the repository\n\n{lines}"


def links(*pairs):
    """Link lines: the newest release first. Each pair is (release, previous release)."""
    lines = [f"[Unreleased]: {URL}v{pairs[0][0]}...HEAD"]
    lines += [f"[{new}]: {URL}v{old}...v{new}" for new, old in pairs]
    return "\n".join(lines) + "\n"


def manifest(name, version, extra=""):
    """A plugin.json in a form that json.dumps does not make, so a rewrite of the whole file shows."""
    return (f'{{\n  "name": "{name}",\n  "version": "{version}",\n  "keywords": ["a", "b"],{extra}\n'
            f'  "author": {{"name": "Owner"}}\n}}\n')


OLD = section("dev-essentials 4.4.3", "5.4.3") + "\n" + section("dev-essentials 4.4.2 and dotnet-backend-dev 1.8.3", "5.4.2")
CHANGELOG = INTRO + OLD + "\n" + links(("5.4.3", "5.4.2"), ("5.4.2", "5.4.1"))
MANIFESTS = {
    DEV: manifest("dev-essentials", "4.4.3"),
    DOTNET: manifest("dotnet-backend-dev", "1.8.3"),
    KB: manifest("kb", "0.2.4"),
}
NEW = section("dev-essentials 4.4.4", "5.4.4", ["the new change"])
RELEASE = ("--release", "5.4.4", "--bump", f"{DEV}=4.4.4")


def path_of(folder):
    return f"{folder}/.claude-plugin/plugin.json"


class SectionCase(ScratchCase):
    def make(self, changelog=CHANGELOG, manifests=None, new=NEW, crlf_changelog=False, crlf_manifests=False):
        """Write the files of a clone and the section file into a new folder. Return the folder."""
        top = self.tmp / f"clone{len(list(self.tmp.iterdir()))}"
        files = {"CHANGELOG.md": changelog.replace("\n", "\r\n") if crlf_changelog else changelog}
        for folder, text in (MANIFESTS if manifests is None else manifests).items():
            files[path_of(folder)] = text.replace("\n", "\r\n") if crlf_manifests else text
        for rel, text in files.items():
            (top / rel).parent.mkdir(parents=True, exist_ok=True)
            (top / rel).write_bytes(text.encode("utf-8"))
        (top / "section.md").write_bytes(new.encode("utf-8"))
        return top

    def tool(self, top, *args, code=0):
        result = run([sys.executable, "-I", SCRIPT, "section", "--repo", top, "--section-file", top / "section.md", *args])
        self.assertResult(result, code)
        return result.stdout

    def files(self, top):
        return {path: path.read_bytes() for path in sorted(top.rglob("*")) if path.is_file()}

    def text(self, top, rel):
        return (top / rel).read_bytes().decode("utf-8")


class SectionTests(SectionCase):
    def test_section_goes_below_unreleased_and_the_links_move(self):
        """Fails for a section or a link line in the wrong place, or for a link line that stays or goes."""
        top = self.make()
        out = self.tool(top, *RELEASE)
        want = INTRO + NEW + "\n" + OLD + "\n" + links(("5.4.4", "5.4.3"), ("5.4.3", "5.4.2"), ("5.4.2", "5.4.1"))
        self.assertEqual(self.text(top, "CHANGELOG.md"), want)
        self.assertEqual(self.text(top, path_of(DEV)), manifest("dev-essentials", "4.4.4"))
        self.assertIn("LINK [5.4.4] compares v5.4.3...v5.4.4\n", out)
        self.assertIn(f"VERSION {path_of(DEV)} 4.4.3 -> 4.4.4\n", out)
        self.assertTrue(out.endswith("RESULT DONE. 2 files written\n"), out)

    def test_each_file_keeps_its_own_line_ends(self):
        """Fails if a file loses its CRLF or LF line ends, or if all files get the line ends of one file."""
        want = INTRO + NEW + "\n" + OLD + "\n" + links(("5.4.4", "5.4.3"), ("5.4.3", "5.4.2"), ("5.4.2", "5.4.1"))
        for crlf_changelog, crlf_manifests in ((True, False), (False, True)):
            with self.subTest(crlf_changelog=crlf_changelog):
                top = self.make(crlf_changelog=crlf_changelog, crlf_manifests=crlf_manifests)
                self.tool(top, *RELEASE)
                self.assertEqual(self.text(top, "CHANGELOG.md"), want.replace("\n", "\r\n") if crlf_changelog else want)
                dev = manifest("dev-essentials", "4.4.4")
                self.assertEqual(self.text(top, path_of(DEV)), dev.replace("\n", "\r\n") if crlf_manifests else dev)

    def test_two_plugins_bump_only_their_own_folders(self):
        """Fails for a bump of the wrong plugin, a missed bump, or a change of another line of a plugin.json."""
        top = self.make(new=section("dev-essentials 4.4.4 and dotnet-backend-dev 1.8.4", "5.4.4"))
        before = self.text(top, path_of(KB))
        self.tool(top, "--release", "5.4.4", "--bump", f"{DEV}=4.4.4", "--bump", f"{DOTNET}=1.8.4")
        self.assertEqual(self.text(top, path_of(DEV)), manifest("dev-essentials", "4.4.4"))
        self.assertEqual(self.text(top, path_of(DOTNET)), manifest("dotnet-backend-dev", "1.8.4"))
        self.assertEqual(self.text(top, path_of(KB)), before)

    def test_unreleased_entries_that_the_section_holds_leave_unreleased(self):
        """Fails if an entry under [Unreleased] stays there, so that the CHANGELOG has it twice."""
        entry = "- the entry of a pull request with no release\n  - its indented line\n"
        changelog = CHANGELOG.replace("## [Unreleased]\n\n", f"## [Unreleased]\n\n### Changed in the repository\n\n{entry}\n")
        top = self.make(changelog=changelog, new=NEW + entry)
        out = self.tool(top, *RELEASE)
        text = self.text(top, "CHANGELOG.md")
        self.assertIn("## [Unreleased]\n\n## dev-essentials 4.4.4 in release [5.4.4]", text)
        self.assertEqual(text.count(entry), 1)
        self.assertIn("ABSORBED - the entry of a pull request with no release\n", out)

    def test_unreleased_entry_that_the_section_lacks_refuses(self):
        """Fails if the script drops an entry under [Unreleased], or its indented line, that the section lacks."""
        entry = "- the entry of a pull request with no release\n  - its indented line\n"
        changelog = CHANGELOG.replace("## [Unreleased]\n\n", f"## [Unreleased]\n\n### Changed in the repository\n\n{entry}\n")
        top = self.make(changelog=changelog, new=NEW + "- the entry of a pull request with no release\n- one more change\n")
        before = self.files(top)
        out = self.tool(top, *RELEASE, code=3)
        self.assertIn("STOP an entry under [Unreleased] is not in the section file. Put it into the section first: "
                      "- the entry of a pull request with no release\n", out)
        self.assertEqual(self.files(top), before)

    def test_second_run_refuses_and_changes_nothing(self):
        """Fails if a second run adds the section a second time, or moves the link lines again."""
        top = self.make()
        self.tool(top, *RELEASE)
        before = self.files(top)
        out = self.tool(top, *RELEASE, code=3)
        self.assertIn("STOP CHANGELOG.md has a heading or a link line of release 5.4.4 already\n", out)
        self.assertEqual(self.files(top), before)

    def test_refusals_write_no_file(self):
        """Fails if a refusal writes a file, or if a check is gone and the script writes a wrong result."""
        two_versions = manifest("kb", "0.2.4", extra='\n  "engine": {\n    "version": "1.0.0"\n  },')
        cases = [
            ("no [Unreleased]", {"changelog": CHANGELOG.replace("## [Unreleased]\n\n", "")}, RELEASE,
             "CHANGELOG.md has 0 lines '## [Unreleased]', not 1"),
            ("two [Unreleased]", {"changelog": CHANGELOG.replace(INTRO, INTRO + "## [Unreleased]\n\n")}, RELEASE,
             "CHANGELOG.md has 2 lines '## [Unreleased]', not 1"),
            ("link at an older release", {"changelog": CHANGELOG.replace("v5.4.3...HEAD", "v5.4.2...HEAD")}, RELEASE,
             "the [Unreleased] link starts at 5.4.2, but the newest release section is 5.4.3"),
            ("release not higher", {"new": section("dev-essentials 4.4.4", "5.4.1")},
             ("--release", "5.4.1", "--bump", f"{DEV}=4.4.4"), "--release 5.4.1 is not higher than the newest release 5.4.3"),
            ("version not higher", {"new": section("dev-essentials 4.4.3", "5.4.4")},
             ("--release", "5.4.4", "--bump", f"{DEV}=4.4.3"), f"{path_of(DEV)}: the version 4.4.3 is not higher than 4.4.3"),
            ("second bump not higher", {"new": section("dev-essentials 4.4.4 and dotnet-backend-dev 1.8.3", "5.4.4")},
             ("--release", "5.4.4", "--bump", f"{DEV}=4.4.4", "--bump", f"{DOTNET}=1.8.3"),
             f"{path_of(DOTNET)}: the version 1.8.3 is not higher than 1.8.3"),
            ("folder with no plugin.json", {}, ("--release", "5.4.4", "--bump", "tools=1.0.0"),
             "the plugin folder tools has no .claude-plugin/plugin.json"),
            ("two version lines", {"manifests": dict(MANIFESTS, **{KB: two_versions}), "new": section("kb 0.2.5", "5.4.4")},
             ("--release", "5.4.4", "--bump", f"{KB}=0.2.5"), f"{path_of(KB)} has 2 '\"version\"' lines, not 1"),
            ("heading of another release", {"new": section("dev-essentials 4.4.4", "5.4.5")}, RELEASE,
             "the heading names release 5.4.5, but --release is 5.4.4"),
            ("heading of another plugin", {}, ("--release", "5.4.4", "--bump", f"{DOTNET}=1.8.4"),
             "the heading names [('dev-essentials', '4.4.4')], but --bump gives [('dotnet-backend-dev', '1.8.4')]"),
            ("second section in the file", {"new": NEW + "\n" + section("dev-essentials 4.4.3", "5.4.3")}, RELEASE,
             "the section file has a second '## ' line: ## dev-essentials 4.4.3 in release [5.4.3] - 2026-11-20"),
            ("no release heading", {"new": "### Changed in the repository\n\n- the change\n"}, RELEASE,
             "the section file does not start with a heading"),
        ]
        for name, files, args, stop in cases:
            with self.subTest(name):
                top = self.make(**files)
                before = self.files(top)
                out = self.tool(top, *args, code=3)
                self.assertIn(f"STOP {stop}", out)
                self.assertTrue(out.endswith("RESULT REFUSED. Nothing changed\n"), out)
                self.assertEqual(self.files(top), before)

    def test_usage_and_setup_errors_exit_2_and_write_nothing(self):
        """Fails if a bad argument or a missing section file ends in a traceback or writes a file."""
        cases = [
            ("same folder twice", ("--section-file", "section.md", "--release", "5.4.4", "--bump", f"{DEV}=4.4.4",
                                   "--bump", f"{DEV}=4.4.5"), "give each --bump folder once"),
            ("missing section file", ("--section-file", "none.md", *RELEASE), "RESULT ERROR. cannot read"),
        ]
        for name, args, text in cases:
            with self.subTest(name):
                top = self.make()
                before = self.files(top)
                result = run([sys.executable, "-I", SCRIPT, "section", "--repo", top, *args], cwd=top)
                self.assertResult(result, 2, text)
                self.assertEqual(self.files(top), before)


FIRST = "## [1.0.0] - 2026-05-04\n\n### Added\n\n- The first plugins.\n"
TAG = "[1.0.0]: https://example.com/owner/repo/releases/tag/v1.0.0\n"
NOTES_CHANGELOG = INTRO + OLD + "\n" + FIRST + "\n" + links(("5.4.3", "5.4.2"), ("5.4.2", "1.0.0")) + TAG
LEAD = "PR #1 closes issue #2."


class NotesTests(ScratchCase):
    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        super().setUp()
        config = self.tmp / "gitconfig"
        config.write_bytes(b"")
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo = git_init(self.tmp / "repo")

    def commit(self, changelog):
        (self.repo / "CHANGELOG.md").write_bytes(changelog.encode("utf-8"))
        run(["git", "-C", self.repo, "add", "CHANGELOG.md"], check=True)
        run(["git", "-C", self.repo, "commit", "-q", "-m", "change"], check=True)

    def notes(self, release, ref="HEAD", code=0):
        out = self.tmp / "notes.md"
        result = run([sys.executable, "-I", SCRIPT, "notes", "--repo", self.repo, "--ref", ref, "--release", release,
                      "--lead", LEAD, "--output", out])
        self.assertResult(result, code)
        return out, result.stdout

    def test_notes_hold_only_the_body_of_the_release(self):
        """Fails if the notes hold the heading, or the next section too."""
        self.commit(NOTES_CHANGELOG)
        body = "The summary of 5.4.3.\n\n### Changed in the repository\n\n- the change\n"
        out, _ = self.notes("5.4.3")
        self.assertEqual(out.read_bytes().decode("utf-8"), f"## What's changed\n\n{LEAD}\n\n{body}")

    def test_notes_of_the_last_section_stop_at_the_link_lines(self):
        """Fails if the notes of the oldest release hold the link lines below it."""
        self.commit(NOTES_CHANGELOG)
        out, _ = self.notes("1.0.0")
        self.assertEqual(out.read_bytes().decode("utf-8"), f"## What's changed\n\n{LEAD}\n\n### Added\n\n- The first plugins.\n")

    def test_notes_read_the_changelog_at_the_ref(self):
        """Fails if the notes come from the work tree or from HEAD, not from --ref."""
        self.commit(NOTES_CHANGELOG)
        self.commit(NOTES_CHANGELOG.replace("The summary of 5.4.3.", "A later summary."))
        out, _ = self.notes("5.4.3", ref="HEAD~1")
        self.assertIn("\nThe summary of 5.4.3.\n", out.read_bytes().decode("utf-8"))

    def test_release_with_no_section_or_two_sections_refuses_and_writes_no_file(self):
        """Fails if the script writes notes for a release that it cannot name in one section."""
        self.commit(NOTES_CHANGELOG.replace(INTRO, INTRO + section("dev-essentials 4.4.3", "5.4.3") + "\n"))
        for release, count in (("5.4.4", 0), ("5.4.3", 2)):
            with self.subTest(release):
                out, stdout = self.notes(release, code=3)
                self.assertIn(f"STOP CHANGELOG.md at HEAD has {count} sections of release {release}, not 1\n", stdout)
                self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
