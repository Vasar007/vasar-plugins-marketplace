"""Tests for tools/changelog_merge.py.

Each test builds a small repository with a CHANGELOG.md and two plugin.json files: a base commit, a commit
of the main branch, and a commit of a work branch. A clone of it merges origin/main into the work branch,
as a thread does before a pull request merges. Then the test runs the script as a child process.
An empty global git configuration and no system configuration keep the settings of the machine out.
"""
import json
import os
import shutil
import stat
import sys
import unittest
from unittest import mock

from support import REPO, tool_missing
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "tools" / "changelog_merge.py"
URL = "https://example.com/owner/repo/compare/"
DEV = "essentials/dev-essentials"
DOTNET = "dotnet/dotnet-backend-dev"
INTRO = "# Changelog\n\nThe intro.\n\n## [Unreleased]\n\n"


def section(plugins, release, bullets, heading="Changed in the repository"):
    lines = "".join(f"- {bullet}\n" for bullet in bullets)
    return f"## {plugins} in release [{release}] - 2026-11-17\n\nThe summary.\n\n### {heading}\n\n{lines}\n"


def links(*pairs):
    """Link lines: the newest release first. Each pair is (release, previous release)."""
    lines = [f"[Unreleased]: {URL}v{pairs[0][0]}...HEAD"]
    lines += [f"[{new}]: {URL}v{old}...v{new}" for new, old in pairs]
    return "\n".join(lines) + "\n"


def manifest(name, version):
    return json.dumps({"name": name, "version": version, "description": "A plugin."}, indent=2) + "\n"


OLD = section("dev-essentials 3.24.0", "4.22.0", ["the old change"])
BASE = {
    f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.0"),
    f"{DOTNET}/.claude-plugin/plugin.json": manifest("dotnet-backend-dev", "1.8.0"),
    "docs/notes.md": "# Notes\n\nThe first line.\n",
    "CHANGELOG.md": INTRO + OLD + links(("4.22.0", "4.21.0")),
}
MAIN_RELEASE = {
    f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1"),
    "docs/notes.md": "# Notes\n\nThe first line.\nThe line of main.\n",
    "CHANGELOG.md": INTRO + section("dev-essentials 3.24.1", "4.22.1", ["the change of main"]) + OLD
    + links(("4.22.1", "4.22.0"), ("4.22.0", "4.21.0")),
}


def branch_release(plugins, bullets=("the change of the branch",), extra=None):
    """The files of a release branch that adds release 4.22.1 with the plugins of the heading."""
    files = {"docs/notes.md": "# Notes\n\nThe first line.\nThe line of the branch.\n",
             "CHANGELOG.md": INTRO + section(plugins, "4.22.1", bullets) + OLD
             + links(("4.22.1", "4.22.0"), ("4.22.0", "4.21.0"))}
    files.update(extra or {})
    return files


MANIFEST = f"{DOTNET}/.claude-plugin/plugin.json"
RELEASE = ("release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
TOP = "## [Unreleased]\n\n"


def described(version, description):
    return json.dumps({"name": "dotnet-backend-dev", "version": version, "description": description}, indent=2) + "\n"


class MergeCase(ScratchCase):
    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        super().setUp()
        config = self.tmp / "gitconfig"
        config.write_bytes(b"")
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, repo, *args, check=True):
        return run(["git", "-C", repo, *args], check=check)

    def commit(self, repo, files, subject):
        for rel, text in files.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", subject)

    def merge(self, branch, main=MAIN_RELEASE, base=BASE, crlf=False, style=None):
        """Build the origin, clone it, and merge origin/main into the branch. Return the clone."""
        origin = git_init(self.tmp / "origin")
        self.git(origin, "config", "core.autocrlf", "false")
        self.git(origin, "checkout", "-q", "-b", "main")
        self.commit(origin, base, "base")
        self.git(origin, "checkout", "-q", "-b", "work")
        self.commit(origin, branch, "work")
        self.git(origin, "checkout", "-q", "main")
        self.commit(origin, main, "main")
        clone = self.tmp / "clone"
        run(["git", "clone", "-q", origin, clone], check=True)
        git_init(clone)
        if crlf:
            self.git(clone, "config", "core.autocrlf", "true")
            for rel in ("CHANGELOG.md", "docs/notes.md"):
                (clone / rel).unlink()
            self.git(clone, "checkout", "--", ".")
        if style:
            self.git(clone, "config", "merge.conflictStyle", style)
        self.git(clone, "checkout", "-q", "work")
        self.git(clone, "merge", "--no-commit", "-q", "origin/main", check=False)
        return clone

    def tool(self, clone, *args, code=0):
        result = run([sys.executable, "-I", SCRIPT, *args, "--repo", clone])
        self.assertResult(result, code)
        return result.stdout

    def text(self, clone, rel):
        return (clone / rel).read_bytes().decode("utf-8")

    def version(self, clone, folder):
        return json.loads(self.text(clone, f"{folder}/.claude-plugin/plugin.json"))["version"]


class ReleaseTests(MergeCase):
    def test_entry_that_main_changed_after_the_branch_took_it_refuses(self):
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- fix the parser\n\n")
        main = {"CHANGELOG.md": base["CHANGELOG.md"].replace("- fix the parser\n", "- fix the lexer\n")}
        branch = branch_release("dotnet-backend-dev 1.8.1", bullets=("the change of the branch", "fix the parser"))
        clone = self.merge(branch, main=main, base=base)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, *RELEASE, "--absorb-unreleased", code=3)
        self.assertIn("the result has a line that a side removed or changed since the merge base, so merge CHANGELOG.md by hand: "
                      "- fix the parser", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_stop_line_names_the_bullet_before_its_indented_line(self):
        base = dict(BASE)
        entry = "### Changed in the repository\n\n- fix the parser\n  - see docs/testing.md\n\n"
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + entry)
        main = {"CHANGELOG.md": base["CHANGELOG.md"].replace("- fix the parser\n", "- fix the lexer\n")}
        branch = branch_release("dotnet-backend-dev 1.8.1", bullets=("the change of the branch", "fix the parser"))
        clone = self.merge(branch, main=main, base=base)
        out = self.tool(clone, *RELEASE, "--absorb-unreleased", code=3)
        self.assertIn("so merge CHANGELOG.md by hand: - fix the parser", out)

    def test_indented_line_below_a_bullet_that_main_has_refuses(self):
        main = {"CHANGELOG.md": BASE["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- a test fix:\n\n")}
        branch = branch_release("dotnet-backend-dev 1.8.1", bullets=("a test fix:", "the change of the branch:"))
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace(":\n", ":\n  - see docs/evals.md\n")
        clone = self.merge(branch, main=main)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, *RELEASE, "--absorb-unreleased", code=3)
        self.assertIn("the result loses a line that a side added since the merge base, so merge CHANGELOG.md by hand: "
                      "  - see docs/evals.md", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_change_of_plugin_json_on_both_sides_is_no_conflict(self):
        main = dict(MAIN_RELEASE)
        main[MANIFEST] = described("1.8.0", "A text of both sides.")
        branch = branch_release("dotnet-backend-dev 1.8.1", extra={MANIFEST: described("1.8.1", "A text of both sides.")})
        clone = self.merge(branch, main=main)
        self.tool(clone, *RELEASE)
        self.assertEqual(self.text(clone, MANIFEST), described("1.8.1", "A text of both sides."))

    def test_release_branch_of_dev_essentials(self):
        clone = self.merge(branch_release("dev-essentials 3.25.0",
                                          extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.25.0")}))
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.25.0", "--release", "4.23.0")
        self.assertIn("RESULT DONE. 2 files written", out)
        text = self.text(clone, "CHANGELOG.md")
        expected_top = (INTRO + section("dev-essentials 3.25.0", "4.23.0", ["the change of the branch"])
                        + section("dev-essentials 3.24.1", "4.22.1", ["the change of main"]))
        self.assertTrue(text.startswith(expected_top), text)
        self.assertTrue(text.endswith(links(("4.23.0", "4.22.1"), ("4.22.1", "4.22.0"), ("4.22.0", "4.21.0"))), text)
        self.assertEqual(self.version(clone, DEV), "3.25.0")
        self.assertIn("<<<<<<< ", self.text(clone, "docs/notes.md"), "a file outside --keep-both stays as it is")
        self.assertIn("CHANGELOG.md", self.git(clone, "ls-files", "-u").stdout, "the script stages nothing")

    def test_release_branch_of_another_plugin(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1",
                                          extra={f"{DOTNET}/.claude-plugin/plugin.json": manifest("dotnet-backend-dev", "1.8.1")}))
        self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
        text = self.text(clone, "CHANGELOG.md")
        self.assertIn("## [Unreleased]\n\n## dotnet-backend-dev 1.8.1 in release [4.22.2] - 2026-11-17\n", text)
        self.assertIn(f"[Unreleased]: {URL}v4.22.2...HEAD\n[4.22.2]: {URL}v4.22.1...v4.22.2\n", text)
        self.assertEqual(self.version(clone, DOTNET), "1.8.1")
        self.assertEqual(self.version(clone, DEV), "3.24.1")

    def test_keep_both_puts_the_side_of_main_first(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2",
                        "--keep-both", "docs/notes.md")
        self.assertIn("KEPT docs/notes.md: both sides of 1 conflicts", out)
        self.assertEqual(self.text(clone, "docs/notes.md"),
                         "# Notes\n\nThe first line.\nThe line of main.\nThe line of the branch.\n")

    def test_keep_both_reads_the_diff3_conflict_style(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), style="diff3")
        self.assertIn("||||||| ", self.text(clone, "docs/notes.md"))
        self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2", "--keep-both", "docs/notes.md")
        self.assertEqual(self.text(clone, "docs/notes.md"),
                         "# Notes\n\nThe first line.\nThe line of main.\nThe line of the branch.\n")

    def test_two_plugins_in_one_release(self):
        clone = self.merge(branch_release("dev-essentials 3.24.1 and dotnet-backend-dev 1.8.1"))
        self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
        self.assertIn("## dev-essentials 3.24.2 and dotnet-backend-dev 1.8.1 in release [4.22.2] - 2026-11-17\n",
                      self.text(clone, "CHANGELOG.md"))
        self.assertEqual((self.version(clone, DEV), self.version(clone, DOTNET)), ("3.24.2", "1.8.1"))

    def test_bullet_of_main_is_dropped_and_its_empty_heading_goes(self):
        main_bullet = "the change of main"
        branch = branch_release("dotnet-backend-dev 1.8.1", bullets=[main_bullet])
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace(
            "- the change of main\n\n", "- the change of main\n\n### Added in dotnet-backend-dev\n\n- a new case\n\n")
        clone = self.merge(branch)
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
        self.assertIn(f"DROPPED - {main_bullet}", out)
        top = self.text(clone, "CHANGELOG.md").split("## dev-essentials 3.24.1")[0]
        self.assertNotIn("### Changed in the repository", top)
        self.assertIn("The summary.\n\n### Added in dotnet-backend-dev\n\n- a new case\n\n", top)

    def test_bullet_with_a_longer_twin_on_main_stays(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1", bullets=["the change"]))
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
        self.assertNotIn("DROPPED", out)
        self.assertIn("### Changed in the repository\n\n- the change\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_crlf_work_tree_keeps_crlf(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), crlf=True)
        self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
        data = (clone / "CHANGELOG.md").read_bytes()
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))

    def test_entries_of_main_under_unreleased_refuse_without_absorb(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(
            "## [Unreleased]\n\n", "## [Unreleased]\n\n### Changed in the repository\n\n- a no-release change\n\n")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), main=main)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2", code=3)
        self.assertIn("pass --absorb-unreleased", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2", "--absorb-unreleased")
        self.assertIn("ABSORBED - a no-release change", out)
        text = self.text(clone, "CHANGELOG.md")
        self.assertIn("## [Unreleased]\n\n## dotnet-backend-dev 1.8.1 in release [4.22.2]", text)
        self.assertIn("### Changed in the repository\n\n- the change of the branch\n- a no-release change\n\n", text)

    def test_wrong_plugin_in_bump_refuses_and_writes_nothing(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        paths = ("CHANGELOG.md", f"{DEV}/.claude-plugin/plugin.json")
        before = [self.text(clone, rel) for rel in paths]
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.25.0", "--release", "4.22.2", code=3)
        self.assertIn("the heading names ['dotnet-backend-dev'], but --bump names ['dev-essentials']", out)
        self.assertEqual([self.text(clone, rel) for rel in paths], before)

    def test_version_that_is_not_higher_refuses(self):
        clone = self.merge(branch_release("dev-essentials 3.24.1"))
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.1", "--release", "4.22.2", code=3)
        self.assertIn("the version 3.24.1 is not higher than 3.24.1", out)

    def test_release_that_is_not_higher_refuses(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.1", code=3)
        self.assertIn("--release 4.22.1 is not higher than the release 4.22.1", out)

    def test_branch_line_outside_its_section_refuses_as_lost(self):
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("- the old change\n", "- the old change\n- a late fix\n")
        clone = self.merge(branch)
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2", code=3)
        self.assertIn("1 lines that the branch added would be lost, the first: - a late fix", out)

    def test_edit_of_main_in_an_old_section_is_no_loss(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the old change", "- the old change, fixed")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), main=main)
        self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2")
        self.assertIn("- the old change, fixed\n", self.text(clone, "CHANGELOG.md"))

    def test_keep_both_file_with_no_conflict_refuses(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2",
                        "--keep-both", f"{DEV}/.claude-plugin/plugin.json", code=3)
        self.assertIn("plugin.json: no conflict to keep both sides of", out)

    def test_changelog_in_keep_both_is_a_usage_error(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        out = run([sys.executable, "-I", SCRIPT, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2",
                   "--keep-both", "CHANGELOG.md", "--repo", clone])
        self.assertResult(out, 2, "do not give it to --keep-both")

    def test_bad_bump_and_unknown_ref_fail_with_code_2(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        self.assertResult(run([sys.executable, "-I", SCRIPT, "release", "--bump", "x=1.2", "--release", "4.22.2"]),
                          2, "give FOLDER=X.Y.Z")
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.2", "--theirs", "nope",
                        code=2)
        self.assertIn("RESULT ERROR. git merge-base", out)

    def test_other_lines_of_plugin_json_of_the_branch_stay(self):
        ours = described("1.8.1", "A new text.")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1", extra={MANIFEST: ours}))
        self.tool(clone, *RELEASE)
        self.assertEqual(self.text(clone, MANIFEST), ours)

    def test_other_lines_of_plugin_json_of_main_stay(self):
        main = dict(MAIN_RELEASE)
        main[MANIFEST] = described("1.8.0", "A text of main.")
        branch = branch_release("dotnet-backend-dev 1.8.1", extra={MANIFEST: manifest("dotnet-backend-dev", "1.8.1")})
        clone = self.merge(branch, main=main)
        self.tool(clone, *RELEASE)
        self.assertEqual(self.text(clone, MANIFEST), described("1.8.1", "A text of main."))

    def test_plugin_json_with_other_changes_on_both_sides_refuses(self):
        main = dict(MAIN_RELEASE)
        main[MANIFEST] = described("1.8.0", "A text of main.")
        branch = branch_release("dotnet-backend-dev 1.8.1", extra={MANIFEST: described("1.8.1", "A text of the branch.")})
        clone = self.merge(branch, main=main)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, *RELEASE, code=3)
        self.assertIn("both sides changed lines other than the version", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_bullet_under_two_headings_of_main_is_absorbed_twice(self):
        block = "### Changed in dev-essentials\n\n- no `icon` key\n\n### Changed in kb\n\n- no `icon` key\n\n"
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, TOP + block)
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), main=main)
        self.tool(clone, *RELEASE, "--absorb-unreleased")
        self.assertIn("- the change of the branch\n\n" + block + "## dev-essentials 3.24.1", self.text(clone, "CHANGELOG.md"))

    def test_absorbed_bullet_keeps_its_indented_lines(self):
        nested = "- the parent entry:\n  - the first child\n  - the second child\n"
        block = "### Changed in the repository\n\n" + nested + "\n"
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + block)
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, TOP + block)
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("- the change of the branch\n",
                                                                nested + "- the change of the branch\n")
        clone = self.merge(branch, main=main, base=base)
        self.tool(clone, *RELEASE, "--absorb-unreleased")
        self.assertIn("### Changed in the repository\n\n- the change of the branch\n" + nested + "\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_no_merge_in_progress_refuses_and_keeps_a_local_edit(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        self.git(clone, "merge", "--abort")
        path = clone / "CHANGELOG.md"
        path.write_bytes(path.read_bytes() + b"A local edit.\n")
        out = self.tool(clone, *RELEASE, code=3)
        self.assertIn("no merge is in progress", out)
        self.assertIn("Run git merge --no-commit origin/main first", out)
        self.assertTrue(self.text(clone, "CHANGELOG.md").endswith("A local edit.\n"))

    def test_theirs_that_is_not_the_merged_commit_refuses(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        before = self.text(clone, "CHANGELOG.md")
        base = self.git(clone, "merge-base", "HEAD", "origin/main").stdout.strip()
        out = self.tool(clone, *RELEASE, "--theirs", base, code=3)
        self.assertIn("the merge in progress takes in", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_versions_compare_as_numbers(self):
        main = dict(MAIN_RELEASE)
        main[f"{DEV}/.claude-plugin/plugin.json"] = manifest("dev-essentials", "3.9.0")
        clone = self.merge(branch_release("dev-essentials 3.10.0"), main=main)
        self.tool(clone, "release", "--bump", f"{DEV}=3.10.0", "--release", "4.22.2")
        self.assertEqual(self.version(clone, DEV), "3.10.0")

    def test_release_number_of_the_branch_that_main_does_not_have(self):
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["CHANGELOG.md"] = (INTRO + section("dotnet-backend-dev 1.8.1", "4.23.0", ["the change of the branch"]) + OLD
                                  + links(("4.23.0", "4.22.0"), ("4.22.0", "4.21.0")))
        clone = self.merge(branch)
        self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.23.0")
        text = self.text(clone, "CHANGELOG.md")
        self.assertIn(f"[Unreleased]: {URL}v4.23.0...HEAD\n[4.23.0]: {URL}v4.22.1...v4.23.0\n[4.22.1]: ", text)
        self.assertNotIn(f"{URL}v4.22.0...v4.23.0", text)

    def test_link_line_of_the_release_that_exists_refuses(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(f"[Unreleased]: {URL}v4.22.1...HEAD",
                                                            f"[Unreleased]: {URL}v4.22.0...HEAD")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), main=main)
        out = self.tool(clone, "release", "--bump", f"{DOTNET}=1.8.1", "--release", "4.22.1", code=3)
        self.assertIn("the link line of release 4.22.1 already exists", out)

    def test_changelog_of_main_with_no_unreleased_heading_refuses(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, "")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), main=main)
        out = self.tool(clone, *RELEASE, code=3)
        self.assertIn("the CHANGELOG.md of --theirs has 0 lines '## [Unreleased]', not 1", out)

    def test_changelog_of_main_with_two_unreleased_headings_refuses(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, TOP + TOP)
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"), main=main)
        out = self.tool(clone, *RELEASE, code=3)
        self.assertIn("the CHANGELOG.md of --theirs has 2 lines '## [Unreleased]', not 1", out)

    def test_entries_of_the_branch_under_unreleased_refuse(self):
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- a late entry\n\n")
        clone = self.merge(branch)
        out = self.tool(clone, *RELEASE, code=3)
        self.assertIn("the branch has entries under [Unreleased]", out)

    def test_branch_with_no_release_section_refuses(self):
        clone = self.merge({"docs/notes.md": "# Notes\n\nThe first line.\nThe line of the branch.\n"})
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.25.0", "--release", "4.22.2", code=3)
        self.assertIn("--theirs has the top section of the branch too", out)

    def test_heading_that_main_took_after_the_merge_base_is_a_new_release(self):
        # Two open branches took release 4.22.1 for now, and the other branch merged first.
        mine = ("- the change of the branch:\n  - see docs/evals.md\n- the second change of the branch\n\n"
                "  The second change also changes the docs.\n")
        branch = branch_release("dev-essentials 3.24.1",
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("- the change of the branch\n", mine)
        clone = self.merge(branch)
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2")
        self.assertNotIn("DROPPED", out)
        top = section("dev-essentials 3.24.2", "4.22.2", ["the change of the branch"]).replace("- the change of the branch\n", mine)
        expected = (INTRO + top + section("dev-essentials 3.24.1", "4.22.1", ["the change of main"]) + OLD
                    + links(("4.22.2", "4.22.1"), ("4.22.1", "4.22.0"), ("4.22.0", "4.21.0")))
        self.assertEqual(self.text(clone, "CHANGELOG.md"), expected)
        self.assertEqual(self.version(clone, DEV), "3.24.2")

    def test_same_heading_and_the_indented_lines_of_main_below_other_bullets_merges(self):
        # The section of main has the summary and the indented lines of the branch too. Each line of the branch stays one time.
        details = ":\n  - see docs/evals.md\n\n  The change also changes the docs.\n"
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the change of main\n", "- the change of main" + details)
        branch = branch_release("dev-essentials 3.24.1",
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("- the change of the branch\n", "- the change of the branch" + details)
        clone = self.merge(branch, main=main)
        self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2")
        top = section("dev-essentials 3.24.2", "4.22.2", ["the change of the branch"]).replace("branch\n", "branch" + details)
        expected = (INTRO + top + main["CHANGELOG.md"][len(INTRO):]).replace(
            f"[Unreleased]: {URL}v4.22.1...HEAD\n", f"[Unreleased]: {URL}v4.22.2...HEAD\n[4.22.2]: {URL}v4.22.1...v4.22.2\n")
        self.assertEqual(self.text(clone, "CHANGELOG.md"), expected)

    def test_section_that_main_has_in_full_refuses(self):
        # After a squash merge of the same branch, main has the heading and each bullet of the branch.
        clone = self.merge(branch_release("dev-essentials 3.24.1", bullets=["the change of main"],
                                          extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")}))
        before = (self.text(clone, "CHANGELOG.md"), self.text(clone, f"{DEV}/.claude-plugin/plugin.json"))
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("STOP the top section of the branch and --theirs both have the entry '- the change of main', "
                      "so merge CHANGELOG.md by hand", out)
        self.assertEqual((self.text(clone, "CHANGELOG.md"), self.text(clone, f"{DEV}/.claude-plugin/plugin.json")), before)

    def test_same_heading_and_one_shared_bullet_refuses(self):
        # A branch that goes on after its own squash merge has the bullets of main and one more bullet.
        clone = self.merge(branch_release("dev-essentials 3.24.1", bullets=["the change of the branch", "the change of main"],
                                          extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")}))
        before = (self.text(clone, "CHANGELOG.md"), self.text(clone, f"{DEV}/.claude-plugin/plugin.json"))
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("STOP the top section of the branch and --theirs both have the entry '- the change of main', "
                      "so merge CHANGELOG.md by hand", out)
        self.assertNotIn("DROPPED", out)
        self.assertEqual((self.text(clone, "CHANGELOG.md"), self.text(clone, f"{DEV}/.claude-plugin/plugin.json")), before)

    def test_same_heading_and_a_bullet_of_main_below_another_heading_refuses(self):
        # The same text below another "### " heading can be the entry of another plugin.
        branch = branch_release("dev-essentials 3.24.1",
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace(
            "- the change of the branch\n", "- the change of the branch\n\n### Fixed in the repository\n\n- the change of main\n")
        clone = self.merge(branch)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("STOP the top section of the branch and --theirs both have the entry '- the change of main', "
                      "so merge CHANGELOG.md by hand", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_heading_and_a_shared_entry_with_a_paragraph_after_a_blank_line_refuses(self):
        loose = "- the shared entry:\n\n  The shared entry also changes the docs.\n"
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the change of main\n", loose)
        branch = branch_release("dev-essentials 3.24.1",
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("- the change of the branch\n",
                                                                "- the change of the branch\n" + loose)
        clone = self.merge(branch, main=main)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("STOP the top section of the branch and --theirs both have the entry '- the shared entry:', "
                      "so merge CHANGELOG.md by hand", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_heading_and_an_unreleased_entry_that_both_sides_released_refuses(self):
        # Both branches moved the entry of the merge base from [Unreleased] into their release section.
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- fix the parser\n\n")
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the change of main\n", "- the change of main\n- fix the parser\n")
        branch = branch_release("dev-essentials 3.24.1", bullets=["the change of the branch", "fix the parser"],
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        clone = self.merge(branch, main=main, base=base)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("STOP the top section of the branch and --theirs both have the entry '- fix the parser', "
                      "so merge CHANGELOG.md by hand", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_heading_and_a_bullet_of_main_with_the_text_of_an_old_release_refuses(self):
        # main added this bullet since the merge base. The old release has its text too.
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the change of main\n",
                                                            "- the change of main\n- the old change\n")
        branch = branch_release("dev-essentials 3.24.1", bullets=["the change of the branch", "the old change", "the change of main"],
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        clone = self.merge(branch, main=main)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("STOP the top section of the branch and --theirs both have the entry '- the old change', "
                      "so merge CHANGELOG.md by hand", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_heading_and_a_bullet_with_the_text_of_an_old_release_is_a_new_entry(self):
        # main did not add this bullet since the merge base, so it is an entry of the branch.
        clone = self.merge(branch_release("dev-essentials 3.24.1", bullets=["the old change"],
                                          extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")}))
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2")
        self.assertNotIn("DROPPED", out)
        self.assertIn("## dev-essentials 3.24.2 in release [4.22.2] - 2026-11-17\n\nThe summary.\n\n"
                      "### Changed in the repository\n\n- the old change\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_section_with_another_date_that_main_has_in_full_refuses(self):
        branch = branch_release("dev-essentials 3.24.1", bullets=["the change of main"],
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("[4.22.1] - 2026-11-17", "[4.22.1] - 2026-11-18")
        clone = self.merge(branch)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", code=3)
        self.assertIn("DROPPED - the change of main", out)
        self.assertIn("STOP the top section of the branch adds no '- ' bullet to --theirs, so the branch adds no release: "
                      "## dev-essentials 3.24.1 in release [4.22.1] - 2026-11-18", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_section_that_main_has_in_full_refuses_before_the_absorb(self):
        # The [Unreleased] entries of main must not make a release of a branch that adds no bullet.
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- a no-release change\n\n")
        branch = branch_release("dev-essentials 3.24.1", bullets=["the change of main"],
                                extra={f"{DEV}/.claude-plugin/plugin.json": manifest("dev-essentials", "3.24.1")})
        clone = self.merge(branch, main=main)
        before = self.text(clone, "CHANGELOG.md")
        for extra in ((), ("--absorb-unreleased",)):
            out = self.tool(clone, "release", "--bump", f"{DEV}=3.24.2", "--release", "4.22.2", *extra, code=3)
            self.assertIn("both have the entry '- the change of main', so merge CHANGELOG.md by hand", out)
            self.assertNotIn("ABSORBED", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_section_with_star_bullets_and_another_heading_merges(self):
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace("- the change of the branch", "* the change of the branch")
        clone = self.merge(branch)
        self.tool(clone, *RELEASE)
        self.assertIn("## dotnet-backend-dev 1.8.1 in release [4.22.2] - 2026-11-17\n\nThe summary.\n\n"
                      "### Changed in the repository\n\n* the change of the branch\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_section_with_no_bullet_and_another_heading_merges(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1", bullets=[]))
        self.tool(clone, *RELEASE)
        self.assertIn("## dotnet-backend-dev 1.8.1 in release [4.22.2] - 2026-11-17\n\nThe summary.\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_keep_both_file_with_a_marker_line_outside_a_conflict_refuses(self):
        notes = "# Notes\n\n=======\n\nThe first line.\n"
        base = dict(BASE, **{"docs/notes.md": notes})
        main = dict(MAIN_RELEASE, **{"docs/notes.md": notes + "The line of main.\n"})
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["docs/notes.md"] = notes + "The line of the branch.\n"
        clone = self.merge(branch, main=main, base=base)
        before = self.text(clone, "docs/notes.md")
        out = self.tool(clone, *RELEASE, "--keep-both", "docs/notes.md", code=3)
        self.assertIn("notes.md: a conflict marker stays after the step", out)
        self.assertEqual(self.text(clone, "docs/notes.md"), before)

    def test_long_output_line_is_cut(self):
        bullet = "a long bullet " + "x" * 300
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the change of main", f"- the change of main\n- {bullet}")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1", bullets=[bullet, "x"]), main=main)
        out = self.tool(clone, *RELEASE)
        self.assertIn("DROPPED - a long bullet " + "x" * 176 + " ... 124 more characters\n", out)

    def test_bump_folder_with_backslashes(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        self.tool(clone, "release", "--bump", DOTNET.replace("/", "\\") + "=1.8.1", "--release", "4.22.2")
        self.assertEqual(self.version(clone, DOTNET), "1.8.1")

    def test_bullet_equal_to_a_bullet_of_an_old_section_stays(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1", bullets=["the old change", "the change of the branch"]))
        out = self.tool(clone, *RELEASE)
        self.assertNotIn("DROPPED", out)
        self.assertIn("### Changed in the repository\n\n- the old change\n- the change of the branch\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_file_that_cannot_be_written_fails_with_code_1(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root writes a read-only file")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        os.chmod(clone / "CHANGELOG.md", stat.S_IREAD)
        out = self.tool(clone, *RELEASE, code=1)
        self.assertIn("RESULT ERROR. 1 of 2 files are written. Cannot write CHANGELOG.md", out)
        os.chmod(clone / "CHANGELOG.md", stat.S_IREAD | stat.S_IWRITE)
        self.tool(clone, *RELEASE)

    def test_keep_both_file_that_is_missing_fails_with_code_2(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, *RELEASE, "--keep-both", "docs/none.md", code=2)
        self.assertIn("RESULT ERROR. cannot read the --keep-both file docs/none.md", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_keep_both_refusal_names_the_path_of_the_file(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        out = self.tool(clone, *RELEASE, "--keep-both", f"{DEV}/.claude-plugin/plugin.json", code=3)
        self.assertIn(f"STOP {DEV}/.claude-plugin/plugin.json: no conflict", out)

    def test_output_is_utf8_without_the_utf8_mode(self):
        bullet = "a bullet \u2014 with \u0436 and \u4e2d"
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace("- the change of main", f"- the change of main\n- {bullet}")
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1", bullets=[bullet, "x"]), main=main)
        result = run([sys.executable, "-I", "-X", "utf8=0", SCRIPT, *RELEASE, "--repo", clone])
        self.assertResult(result, 0, f"DROPPED - {bullet}")

    def test_help_prints_the_exit_codes(self):
        self.assertResult(run([sys.executable, "-I", SCRIPT, "--help"]), 0, "Exit codes:", "STOP")

    def test_same_bump_folder_twice_is_a_usage_error(self):
        result = run([sys.executable, "-I", SCRIPT, "release", "--bump", f"{DEV}=3.25.0", "--bump", f"{DEV}=3.26.0",
                      "--release", "4.22.2"])
        self.assertResult(result, 2, "give each --bump folder once")


class UnreleasedTests(MergeCase):
    def branch(self, block):
        return {"CHANGELOG.md": BASE["CHANGELOG.md"].replace("## [Unreleased]\n\n", "## [Unreleased]\n\n" + block)}

    def test_entries_of_the_branch_go_under_unreleased_of_main(self):
        clone = self.merge(self.branch("### Changed in the repository\n\n- a test fix\n\n"))
        out = self.tool(clone, "unreleased")
        self.assertIn("ADDED - a test fix", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), MAIN_RELEASE["CHANGELOG.md"].replace(
            "## [Unreleased]\n\n", "## [Unreleased]\n\n### Changed in the repository\n\n- a test fix\n\n"))

    def test_entries_of_both_sides_stay(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(
            "## [Unreleased]\n\n", "## [Unreleased]\n\n### Changed in the repository\n\n- a change of main\n\n")
        clone = self.merge(self.branch("### Changed in the repository\n\n- a test fix\n\n### Added in the repository"
                                       "\n\n- a new page\n\n"), main=main)
        self.tool(clone, "unreleased")
        self.assertIn("## [Unreleased]\n\n### Changed in the repository\n\n- a change of main\n- a test fix\n\n"
                      "### Added in the repository\n\n- a new page\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_branch_with_a_release_section_refuses(self):
        clone = self.merge(branch_release("dotnet-backend-dev 1.8.1"))
        out = self.tool(clone, "unreleased", code=3)
        self.assertIn("the branch has no entries under [Unreleased]", out)

    def test_entry_that_main_moved_into_a_release_does_not_come_back(self):
        block = "### Changed in the repository\n\n- an entry of the base\n\n"
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + block)
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = (INTRO + "### Changed in the repository\n\n- a new entry of main\n\n"
                                + section("dev-essentials 3.24.1", "4.22.1", ["the change of main", "an entry of the base"])
                                + OLD + links(("4.22.1", "4.22.0"), ("4.22.0", "4.21.0")))
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace("- an entry of the base\n",
                                                               "- a test fix\n- an entry of the base\n")}
        clone = self.merge(branch, main=main, base=base)
        self.assertIn("<<<<<<< ", self.text(clone, "CHANGELOG.md"), "the merge must have a conflict")
        self.tool(clone, "unreleased")
        text = self.text(clone, "CHANGELOG.md")
        self.assertEqual(text.count("- an entry of the base\n"), 1, text)
        self.assertIn(TOP + "### Changed in the repository\n\n- a new entry of main\n- a test fix\n\n## dev-essentials 3.24.1", text)

    def test_same_bullet_under_two_headings_stays_twice(self):
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, TOP + "### Changed in kb\n\n- an entry of main\n\n")
        block = "### Changed in dev-essentials\n\n- no `icon` key\n\n### Changed in kb\n\n- no `icon` key\n\n"
        clone = self.merge(self.branch(block), main=main)
        self.tool(clone, "unreleased")
        self.assertIn(TOP + "### Changed in kb\n\n- an entry of main\n- no `icon` key\n\n"
                      "### Changed in dev-essentials\n\n- no `icon` key\n\n## dev-essentials 3.24.1", self.text(clone, "CHANGELOG.md"))

    def test_merge_with_no_conflict_in_the_changelog_runs(self):
        block = "### Changed in the repository\n\n- an entry of the base\n\n"
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + block)
        release = "## dev-essentials 3.24.1 in release [4.22.1] - 2026-11-17\n\nThe summary.\n\n"
        main = {"CHANGELOG.md": base["CHANGELOG.md"].replace(TOP + block, TOP + release + block).replace(
            f"[Unreleased]: {URL}v4.22.0...HEAD\n", f"[Unreleased]: {URL}v4.22.1...HEAD\n[4.22.1]: {URL}v4.22.0...v4.22.1\n")}
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace("- an entry of the base\n", "- an entry of the base\n- a test fix\n")}
        clone = self.merge(branch, main=main, base=base)
        self.assertEqual(self.git(clone, "ls-files", "-u").stdout, "", "git must merge with no conflict")
        self.tool(clone, "unreleased")
        self.assertIn(TOP + "### Changed in the repository\n\n- a test fix\n\n" + release + block, self.text(clone, "CHANGELOG.md"))

    def test_new_entry_equal_to_an_entry_that_main_released_stays(self):
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + "### Changed in dev-essentials\n\n- no `icon` key\n\n")
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = (INTRO + "### Changed in the repository\n\n- a new entry of main\n\n"
                                + section("dev-essentials 3.24.1", "4.22.1", ["no `icon` key"], heading="Changed in dev-essentials")
                                + OLD + links(("4.22.1", "4.22.0"), ("4.22.0", "4.21.0")))
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace(
            "- no `icon` key\n", "- no `icon` key\n\n### Changed in kb\n\n- no `icon` key\n- a kb fix:\n  - see the docs\n")}
        clone = self.merge(branch, main=main, base=base)
        self.tool(clone, "unreleased")
        self.assertIn(TOP + "### Changed in the repository\n\n- a new entry of main\n\n"
                      "### Changed in kb\n\n- no `icon` key\n- a kb fix:\n  - see the docs\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_entry_that_main_moved_to_another_heading_is_not_doubled(self):
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- an entry of the base\n\n")
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(TOP, TOP + "### Fixed in the repository\n\n- an entry of the base\n\n")
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace("- an entry of the base\n", "- an entry of the base\n- a test fix\n")}
        clone = self.merge(branch, main=main, base=base)
        self.tool(clone, "unreleased")
        self.assertIn(TOP + "### Fixed in the repository\n\n- an entry of the base\n\n"
                      "### Changed in the repository\n\n- a test fix\n\n## dev-essentials 3.24.1", self.text(clone, "CHANGELOG.md"))

    def test_new_indented_line_below_a_bullet_of_main_refuses(self):
        nested = "- the parent entry:\n  - the first child\n"
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = main["CHANGELOG.md"].replace(
            TOP, TOP + "### Changed in the repository\n\n" + nested + "- an entry of main\n\n")
        branch = {"CHANGELOG.md": BASE["CHANGELOG.md"].replace(
            TOP, TOP + "### Changed in the repository\n\n" + nested + "  - a child of the branch\n\n")}
        clone = self.merge(branch, main=main)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "unreleased", code=3)
        self.assertIn("both sides have the entry '- the parent entry:' with other indented lines", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_entry_of_the_base_that_the_branch_changed_refuses(self):
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- fix the parser\n\n")
        main = {"CHANGELOG.md": base["CHANGELOG.md"].replace(
            "- fix the parser\n", "- fix the parser\n\n### Changed in kb\n\n- an entry of main\n")}
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace("- fix the parser\n", "- fix the lexer\n")}
        clone = self.merge(branch, main=main, base=base)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "unreleased", code=3)
        self.assertIn("the branch changed or removed an entry of the merge base, so merge CHANGELOG.md by hand: "
                      "- fix the parser", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_same_bullet_with_another_indented_line_that_an_old_release_has_refuses(self):
        old = OLD.replace("- the old change\n", "- the old change:\n  - see docs/testing.md\n")
        base = {"CHANGELOG.md": INTRO + old + links(("4.22.0", "4.21.0"))}
        main = {"CHANGELOG.md": base["CHANGELOG.md"].replace(
            TOP, TOP + "### Changed in the repository\n\n- a test fix:\n  - see docs/evals.md\n\n")}
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace(
            TOP, TOP + "### Changed in the repository\n\n- a test fix:\n  - see docs/testing.md\n\n")}
        clone = self.merge(branch, main=main, base=base)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "unreleased", code=3)
        self.assertIn("both sides have the entry '- a test fix:' with other indented lines", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_new_entry_with_an_indented_line_of_a_released_entry_keeps_it(self):
        entry = "- an entry of the base:\n  - see docs/testing.md\n"
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n" + entry + "\n")
        main = dict(MAIN_RELEASE)
        main["CHANGELOG.md"] = (INTRO + section("dev-essentials 3.24.1", "4.22.1", ["an entry of the base:"]).replace(
            "- an entry of the base:\n", entry) + OLD + links(("4.22.1", "4.22.0"), ("4.22.0", "4.21.0")))
        branch = {"CHANGELOG.md": base["CHANGELOG.md"].replace(entry, entry + "- a test fix:\n  - see docs/testing.md\n")}
        clone = self.merge(branch, main=main, base=base)
        self.tool(clone, "unreleased")
        self.assertIn(TOP + "### Changed in the repository\n\n- a test fix:\n  - see docs/testing.md\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_line_of_only_spaces_in_the_branch_block_is_no_refusal(self):
        clone = self.merge(self.branch("### Changed in the repository\n\n- a test fix\n  \n\n"))
        self.tool(clone, "unreleased")
        self.assertIn(TOP + "### Changed in the repository\n\n- a test fix\n\n## dev-essentials 3.24.1",
                      self.text(clone, "CHANGELOG.md"))

    def test_line_that_the_branch_removed_from_a_release_refuses(self):
        base = dict(BASE)
        base["CHANGELOG.md"] = base["CHANGELOG.md"].replace("- the old change\n", "- the old change\n- a wrong entry\n")
        main = {"docs/notes.md": "# Notes\n\nThe first line.\nThe line of main.\n"}
        branch = {"CHANGELOG.md": BASE["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- a new entry\n\n")}
        clone = self.merge(branch, main=main, base=base)
        before = self.text(clone, "CHANGELOG.md")
        out = self.tool(clone, "unreleased", code=3)
        self.assertIn("the result has a line that a side removed or changed since the merge base, so merge CHANGELOG.md by hand: "
                      "- a wrong entry", out)
        self.assertEqual(self.text(clone, "CHANGELOG.md"), before)

    def test_branch_with_entries_and_a_release_section_refuses(self):
        branch = branch_release("dotnet-backend-dev 1.8.1")
        branch["CHANGELOG.md"] = branch["CHANGELOG.md"].replace(TOP, TOP + "### Changed in the repository\n\n- a late entry\n\n")
        clone = self.merge(branch)
        out = self.tool(clone, "unreleased", code=3)
        self.assertIn("the branch adds a release section, so use the subcommand release", out)


if __name__ == "__main__":
    unittest.main()
