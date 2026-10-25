"""Checks that each plugin with a changed file has a higher version in its plugin.json than at the base.

The base is the merge base with origin/<GITHUB_BASE_REF> in a CI pull request, else with $VERSION_BUMP_BASE or origin/main.
A CI run with no pull request skips the check, because the pull request already ran it.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import IN_CI, REPO, tool_missing

MANIFEST = ".claude-plugin/plugin.json"
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")


def parse_version(text):
    match = VERSION.match(text or "")
    if not match:
        raise ValueError(f"version {text!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(part) for part in match.groups())


def changed_plugins(paths, roots):
    """The plugin roots, as 'group/plugin' paths, that hold at least one of the changed paths."""
    return sorted({root for root in roots for path in paths if path.startswith(root + "/")})


def plugin_roots(repo, revision=None):
    """The 'group/plugin' paths of the plugins in the work tree, or at a commit."""
    if revision is None:
        return sorted(p.parent.parent.relative_to(repo).as_posix() for p in Path(repo).glob(f"*/*/{MANIFEST}"))
    out = git(repo, "ls-tree", "-r", "--name-only", revision).stdout.splitlines()
    return sorted(path[:-len(MANIFEST) - 1] for path in out if path.count("/") == 3 and path.endswith(MANIFEST))


def version_at(repo, root, revision=None):
    """The version in the plugin.json of a plugin, in the work tree or at a commit. None if the file is missing."""
    if revision is None:
        path = Path(repo) / root / MANIFEST
        text = path.read_text(encoding="utf-8") if path.is_file() else None
    else:
        shown = git(repo, "show", f"{revision}:{root}/{MANIFEST}")
        text = shown.stdout if shown.returncode == 0 else None
    return None if text is None else json.loads(text).get("version")


def bump_problems(repo, base):
    """One line for each changed plugin whose version did not go up since the base commit."""
    changed = git(repo, "diff", "--name-only", "--no-renames", "-z", base).stdout.split("\0")
    roots = sorted(set(plugin_roots(repo)) | set(plugin_roots(repo, base)))
    problems = []
    for root in changed_plugins([p for p in changed if p], roots):
        old, new = version_at(repo, root, base), version_at(repo, root)
        if old is None or new is None:
            continue
        try:
            if parse_version(new) <= parse_version(old):
                problems.append(f"{root}: files changed, but the version is {new}, and it was {old} at the base. "
                                f"Raise the version in {root}/{MANIFEST}.")
        except ValueError as exc:
            problems.append(f"{root}: {exc}")
    return problems


def base_ref():
    """The branch to compare with, or None when the check does not apply."""
    if os.environ.get("VERSION_BUMP_BASE"):
        return os.environ["VERSION_BUMP_BASE"]
    if os.environ.get("GITHUB_BASE_REF"):
        return f"origin/{os.environ['GITHUB_BASE_REF']}"
    return None if IN_CI else "origin/main"


class VersionRuleTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("3.10.2"), (3, 10, 2))
        self.assertLess(parse_version("3.9.9"), parse_version("3.10.0"))
        for bad in ("3.1", "v3.1.0", "3.1.0-beta", "", None):
            with self.subTest(version=bad):
                self.assertRaises(ValueError, parse_version, bad)

    def test_changed_plugins(self):
        roots = ["dotnet/dotnet-backend-dev", "essentials/dev-essentials", "essentials/dev-essentials-extra"]
        paths = ["README.md", "essentials/dev-essentials-extra/skills/a/SKILL.md",
                 "essentials/dev-essentials/evals/triggers/a/prompt.md", "tests/test_a.py"]
        self.assertEqual(changed_plugins(paths, roots),
                         ["essentials/dev-essentials", "essentials/dev-essentials-extra"])


class BumpProblemsTests(unittest.TestCase):
    """bump_problems on a temporary repository with two plugins."""

    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.write("essentials/one/.claude-plugin/plugin.json", '{"name": "one", "version": "1.2.3"}\n')
        self.write("essentials/one/skills/a/SKILL.md", "first\n")
        self.write("dotnet/two/.claude-plugin/plugin.json", '{"name": "two", "version": "2.0.0"}\n')
        self.write("dotnet/two/agents/b.md", "first\n")
        self.write("README.md", "first\n")
        self.git("init", "-q")
        self.commit("base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.com",
                               *args], capture_output=True, text=True, check=True).stdout

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def test_change_outside_the_plugins_needs_no_bump(self):
        self.write("README.md", "second\n")
        self.commit("readme")
        self.assertEqual(bump_problems(self.repo, self.base), [])

    def test_changed_plugin_without_a_bump_fails(self):
        self.write("essentials/one/skills/a/SKILL.md", "second\n")
        self.commit("skill")
        self.assertEqual(bump_problems(self.repo, self.base), [
            "essentials/one: files changed, but the version is 1.2.3, and it was 1.2.3 at the base. "
            "Raise the version in essentials/one/.claude-plugin/plugin.json."])

    def test_bumped_plugin_passes_and_other_plugin_is_not_checked(self):
        self.write("essentials/one/skills/a/SKILL.md", "second\n")
        self.write("essentials/one/.claude-plugin/plugin.json", '{"name": "one", "version": "1.2.4"}\n')
        self.commit("skill and bump")
        self.assertEqual(bump_problems(self.repo, self.base), [])

    def test_lower_version_fails(self):
        self.write("dotnet/two/agents/b.md", "second\n")
        self.write("dotnet/two/.claude-plugin/plugin.json", '{"name": "two", "version": "1.9.0"}\n')
        self.commit("lower")
        self.assertEqual(len(bump_problems(self.repo, self.base)), 1)

    def test_new_file_in_a_plugin_counts(self):
        self.write("dotnet/two/evals/triggers/c/prompt.md", "new\n")
        self.commit("new case")
        self.assertEqual(len(bump_problems(self.repo, self.base)), 1)

    def test_skill_moved_between_plugins_needs_a_bump_in_both(self):
        self.git("mv", "essentials/one/skills/a/SKILL.md", "dotnet/two/skills-a-SKILL.md")
        self.write("dotnet/two/.claude-plugin/plugin.json", '{"name": "two", "version": "2.0.1"}\n')
        self.commit("move")
        problems = bump_problems(self.repo, self.base)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("essentials/one: files changed"))

    def test_uncommitted_change_counts(self):
        self.write("dotnet/two/agents/b.md", "second\n")
        self.assertEqual(len(bump_problems(self.repo, self.base)), 1)

    def test_new_and_removed_plugins_need_no_bump(self):
        self.write("workflows/three/.claude-plugin/plugin.json", '{"name": "three", "version": "1.0.0"}\n')
        shutil.rmtree(self.repo / "dotnet")
        self.commit("add three, remove two")
        self.assertEqual(bump_problems(self.repo, self.base), [])

    def test_version_that_is_not_semver_fails(self):
        self.write("essentials/one/.claude-plugin/plugin.json", '{"name": "one", "version": "1.3"}\n')
        self.commit("bad version")
        self.assertEqual(bump_problems(self.repo, self.base), ["essentials/one: version '1.3' is not MAJOR.MINOR.PATCH"])


class RepositoryTest(unittest.TestCase):
    def test_changed_plugins_bump_their_version(self):
        ref = base_ref()
        if ref is None:
            self.skipTest("not a pull request. The pull request run checks the versions.")
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        merge_base = git(REPO, "merge-base", ref, "HEAD")
        if merge_base.returncode != 0:
            tool_missing(self, f"cannot find the merge base with {ref}. Fetch {ref}, or set VERSION_BUMP_BASE. "
                               f"{merge_base.stderr.strip()}")
        problems = bump_problems(REPO, merge_base.stdout.strip())
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
