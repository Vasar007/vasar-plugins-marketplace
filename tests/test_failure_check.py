"""Tests for essentials/dev-essentials/skills/review-loop/scripts/failure_check.py.

Each test builds a git repository in a temporary folder with a base commit and
a fix commit, and runs the script as a child process, as Phase 6 of review-loop
does. The commands are short bash lines, so no test builds a project.
"""
import contextlib
import io
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock

from support import REPO, load_module, run_with_open_stdin, tool_missing
from testkit import ScratchCase, clean_env, git_init, remove_tree, run

SCRIPT = REPO / "essentials/dev-essentials/skills/review-loop/scripts/failure_check.py"
SKILL = SCRIPT.parent.parent / "SKILL.md"
fc = load_module("failure_check", SCRIPT)
FAIL_WITH = "cat msg.txt; exit $(cat code.txt)"
CHECK = 'grep -q good value.txt || { echo "error: value.txt is $(cat value.txt)"; exit 1; }'
UNITTEST = shlex.quote(Path(sys.executable).as_posix()) + " -B -m unittest discover -s tests"
CALC_TESTS = """import unittest


class CalcTests(unittest.TestCase):
    def test_add(self):
        {}

    def test_sub(self):
        self.assertEqual(2 - 1, 1)
"""
MORE_TESTS = """

class MoreTests(unittest.TestCase):
    def test_mul(self):
        self.assertEqual(2 * 2, 4)
"""
# The hit lines of ruff 0.17.6 on Windows, as `ruff check --output-format concise` prints them.
RUFF_OS = "src\\a.py:1:8: F401 [*] `os` imported but unused"
RUFF_SYS = "src\\a.py:1:8: F401 [*] `sys` imported but unused"
RUFF_JSON = "src\\errors.py:1:8: F401 [*] `json` imported but unused"


def ruff_concise(*hits):
    """The whole output of ruff with the given hit lines and its summary lines."""
    noun = "error" if len(hits) == 1 else "errors"
    return [*hits, f"Found {len(hits)} {noun}.", f"[*] {len(hits)} fixable with `--fix`."]


class FailureCheckCase(ScratchCase):
    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        if fc.find_bash() is None:
            tool_missing(self, "bash not found")
        super().setUp()
        self.temp = self.tmp / "temp"
        self.temp.mkdir()
        self.env = clean_env(TMPDIR=str(self.temp), TEMP=str(self.temp), TMP=str(self.temp))
        self.repo = git_init(self.tmp / "repo")
        self.write("sub/value.txt", "good\n")
        self.base = self.commit("base")

    def git(self, *args):
        return run(["git", "-C", self.repo, *args], check=True).stdout.strip()

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def check(self, fix, command=CHECK, *extra, code=0, cwd="sub", launch=("-I",), env=None):
        args = [sys.executable, *launch, SCRIPT, "--fix-commit", fix, "--command", command, "--cwd", self.repo / cwd]
        result = run([*args, *extra], env=env or self.env, timeout=120)
        self.assertResult(result, code)
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1, "a worktree is left")
        self.assertEqual(list(self.temp.iterdir()), [], "a temporary folder is left")
        return result.stdout

    def verdict(self, out):
        return re.search(r"^VERDICT: (\S+)$", out, re.M).group(1)

    def fail_with(self, parent_text, fix_text, parent_code=1, fix_code=1):
        """Commit a parent and a fix commit that fail with the given text and exit code. The command is FAIL_WITH."""
        self.write("sub/msg.txt", parent_text)
        self.write("sub/code.txt", f"{parent_code}\n")
        self.commit("parent")
        self.write("sub/msg.txt", fix_text)
        self.write("sub/code.txt", f"{fix_code}\n")
        return self.commit("fix")

    def unittest_fix(self, parent_assert, fix_assert):
        """Commit a parent and a fix commit whose test_add runs the given assert. The fix commit adds one more test."""
        self.write("sub/tests/test_calc.py", CALC_TESTS.format(parent_assert))
        self.commit("parent")
        self.write("sub/tests/test_calc.py", CALC_TESTS.format(fix_assert) + MORE_TESTS)
        return self.commit("fix")


class VerdictTests(FailureCheckCase):
    def test_failure_that_the_fix_brings_is_a_regression(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        out = self.check(fix)
        self.assertEqual(self.verdict(out), "REGRESSION")
        self.assertIn("MAIN WORKTREE: clean", out)
        self.assertRegex(out, r"RUN fix \w+ in main worktree .*[/\\]repo[/\\]sub: exit 1 ")
        self.assertIn("ERROR | error: value.txt is bad", out)
        self.assertIn("TAIL  | error: value.txt is bad", out)
        self.assertRegex(out, r"RUN parent \w+ in temporary worktree .*review-loop-fc-\S+[/\\]parent[/\\]sub: exit 0")

    def test_error_text_on_stderr_is_in_the_report(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        out = self.check(fix, 'grep -q good value.txt || { echo "error: on stderr" >&2; exit 1; }')
        self.assertEqual(self.verdict(out), "REGRESSION")
        self.assertIn("ERROR | error: on stderr", out)

    def test_failure_of_uncommitted_changes_points_to_the_main_worktree(self):
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.write("sub/value.txt", "broken by hand\n")
        out = self.check(fix)
        self.assertEqual(self.verdict(out), "UNCOMMITTED")
        self.assertIn("CHANGED: sub/value.txt", out)
        self.assertRegex(out, r"RUN fix \w+ in temporary worktree .*review-loop-fc-\w+[/\\]fix[/\\]sub: exit 0 ")
        self.assertNotIn("RUN parent", out)

    def test_head_that_is_not_the_fix_commit_is_not_clean(self):
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.write("sub/value.txt", "bad\n")
        self.commit("later")
        out = self.check(fix)
        self.assertIn(", not the fix commit", out)
        self.assertEqual(self.verdict(out), "UNCOMMITTED")

    def test_same_failure_at_both_commits(self):
        self.write("sub/value.txt", "bad\n")
        self.commit("break")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        out = self.check(fix)
        self.assertEqual(self.verdict(out), "SAME-AT-PARENT")

    def test_same_failure_with_a_space_in_the_temporary_folder(self):
        self.temp = self.tmp / "my temp"
        self.temp.mkdir()
        env = clean_env(TMPDIR=str(self.temp), TEMP=str(self.temp), TMP=str(self.temp))
        self.write("sub/value.txt", "bad\n")
        self.commit("break")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        command = ('d=$PWD; if command -v cygpath > /dev/null; then d=$(cygpath -w "$d"); fi; '
                   'grep -q good value.txt || { echo "error in $d/value.txt"; exit 1; }')
        out = self.check(fix, command, env=env)
        self.assertEqual(self.verdict(out), "SAME-AT-PARENT")

    def test_other_error_at_the_parent_is_other(self):
        self.write("sub/value.txt", "worse\n")
        self.commit("break")
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.assertEqual(self.verdict(self.check(fix)), "OTHER")

    def test_output_that_is_not_ascii_gives_a_verdict_when_the_stream_is_ascii(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        command = r"grep -q good value.txt || { printf 'error: \xe2\x9c\x97 x\n'; exit 1; }"
        env = clean_env(PYTHONIOENCODING="ascii", TMPDIR=str(self.temp), TEMP=str(self.temp), TMP=str(self.temp))
        out = self.check(fix, command, launch=(), env=env)
        self.assertEqual(self.verdict(out), "REGRESSION")
        self.assertIn("\u2717", out)

    def test_same_unittest_failure_after_a_new_test_is_same_at_parent(self):
        fix = self.unittest_fix("self.assertEqual(1 + 1, 3)", "self.assertEqual(1 + 1, 3)")
        out = self.check(fix, UNITTEST)
        self.assertRegex(out, r"TAIL  \| Ran 3 tests in ")
        self.assertRegex(out, r"TAIL  \| Ran 2 tests in ")
        self.assertEqual(self.verdict(out), "SAME-AT-PARENT")

    def test_other_unittest_failure_after_a_new_test_is_other(self):
        fix = self.unittest_fix("self.assertEqual(1 + 1, 3)", "self.assertEqual(2 + 2, 5)")
        out = self.check(fix, UNITTEST)
        self.assertIn("ERROR | AssertionError: 4 != 5", out)
        self.assertEqual(self.verdict(out), "OTHER")

    def test_two_errors_with_different_class_names_are_not_the_same(self):
        fix = self.fail_with("Traceback (most recent call last):\nValueError: parent bug\n",
                             "Traceback (most recent call last):\nKeyError: 'missing'\n")
        self.assertEqual(self.verdict(self.check(fix, FAIL_WITH)), "OTHER")

    def test_two_failures_that_differ_only_in_the_last_lines_are_not_the_same(self):
        fix = self.fail_with("FAIL src/a.test.js\n* math > adds\nTests: 1 failed, 3 passed, 4 total\n",
                             "FAIL src/a.test.js\n* parser > reads\nTests: 1 failed, 3 passed, 4 total\n")
        self.assertEqual(self.verdict(self.check(fix, FAIL_WITH)), "OTHER")

    def test_same_error_with_another_exit_code_is_other(self):
        fix = self.fail_with("error: boom\n", "error: boom\n", parent_code=1, fix_code=2)
        self.assertEqual(self.verdict(self.check(fix, FAIL_WITH)), "OTHER")

    def test_failure_with_no_output_at_both_commits_is_other(self):
        self.write("sub/value.txt", "bad\n")
        self.commit("break")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.assertEqual(self.verdict(self.check(fix, "exit 1")), "OTHER")

    def test_two_lint_hits_that_differ_only_in_a_byte_that_is_not_utf8_are_other(self):
        hit = b"src/caf%s.py:1:1: F401 'os' imported but unused\n"
        self.write("sub/code.txt", "1\n")
        (self.repo / "sub/msg.txt").write_bytes(hit % b"\xe8")
        self.commit("parent")
        (self.repo / "sub/msg.txt").write_bytes(hit % b"\xe9")
        fix = self.commit("fix")
        out = self.check(fix, FAIL_WITH)
        self.assertIn("TAIL  | src/caf\\xe9.py:1:1: F401", out)
        self.assertIn("TAIL  | src/caf\\xe8.py:1:1: F401", out)
        self.assertEqual(self.verdict(out), "OTHER")

    def test_more_than_twenty_error_lines_are_cut(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        command = 'grep -q good value.txt || { for i in $(seq 25); do echo "error $i"; done; exit 1; }'
        out = self.check(fix, command)
        self.assertEqual(len(re.findall(r"^  ERROR \| error \d+$", out, re.M)), 20)
        self.assertIn("ERROR | ... 5 more error lines", out)
        self.assertEqual(re.findall(r"^  TAIL  \| error (\d+)$", out, re.M), [str(i) for i in range(11, 26)])

    def test_output_line_over_300_characters_is_cut(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        out = self.check(fix, "grep -q good value.txt || { printf 'error: %05000d\\n' 7; exit 1; }")
        self.assertEqual(self.verdict(out), "REGRESSION")
        cut = "error: " + "0" * 293 + " ... 4707 more characters"
        self.assertEqual(re.findall(r"^  (?:ERROR|TAIL ) \| (.*)$", out, re.M), [cut, cut])

    def test_two_errors_that_differ_only_after_the_cut_are_not_the_same(self):
        start = "error: " + "x" * fc.LINE_CHARS
        fix = self.fail_with(start + " in a.py\n", start + " in b.py\n")
        out = self.check(fix, FAIL_WITH)
        self.assertEqual(self.verdict(out), "OTHER")
        self.assertEqual(re.findall(r"^  ERROR \| (.*)$", out, re.M), [fc.cut(start + " in a.py")] * 2)

    def test_command_that_cannot_start_is_other_with_no_parent_run(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        out = self.check(fix, "no-such-tool-xyz --build")
        self.assertEqual(self.verdict(out), "OTHER")
        self.assertIn("exit 127", out)
        self.assertNotIn("RUN parent", out)

    def test_second_run_that_passes_in_a_clean_worktree_is_other(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        out = self.check(fix, "true")
        self.assertEqual(self.verdict(out), "OTHER")

    def test_folder_missing_at_the_parent_is_other(self):
        self.write("new/value.txt", "bad\n")
        fix = self.commit("fix")
        out = self.check(fix, cwd="new")
        self.assertIn("does not exist at this commit", out)
        self.assertEqual(self.verdict(out), "OTHER")
        self.assertIn("REASON: the command did not run to an end at the commit before the fix commit.", out)


class IgnoreAndLimitTests(FailureCheckCase):
    def test_ignored_files_of_the_loop_do_not_count(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("Notes/Reviews/branch-cycle-1.md", "report\n")
        out = self.check(fix, CHECK, "--ignore", "Notes/Reviews/branch-*")
        self.assertIn("MAIN WORKTREE: clean", out)
        self.assertNotIn("CHANGED:", out)

    def test_more_than_twenty_changed_paths_are_cut(self):
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        for i in range(25):
            self.write(f"new/f{i:02}.txt", "x\n")
        out = self.check(fix, "true")
        self.assertEqual(re.findall(r"^CHANGED: (.*)$", out, re.M),
                         [f"new/f{i:02}.txt" for i in range(20)] + ["... 5 more paths"])

    def test_changed_path_with_a_line_break_is_one_line(self):
        if os.name == "nt":
            self.skipTest("a file name on Windows cannot have a line break")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.write("a\nVERDICT: REGRESSION", "x\n")
        out = self.check(fix, "true")
        self.assertIn('CHANGED: "a\\nVERDICT: REGRESSION"\n', out)
        self.assertEqual(re.findall(r"^VERDICT: .*$", out, re.M), ["VERDICT: UNCOMMITTED"])

    def test_time_limit_stops_the_command(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        start = time.monotonic()
        out = self.check(fix, "sleep 60", "--timeout", "2")
        self.assertLess(time.monotonic() - start, 45)
        self.assertRegex(out, r"stopped after the time limit of 2 s \(([2-9]|\d\d) s with the stop\)")
        self.assertNotIn("RUN parent", out)
        self.assertEqual(self.verdict(out), "OTHER")

    def test_program_of_git_that_reads_input_does_not_block_the_script(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        reader = self.tmp / "read-input"
        reader.write_bytes(b"#!/bin/sh\ncat > /dev/null\n")
        os.chmod(reader, 0o755)
        self.git("config", "core.fsmonitor", shlex.quote(reader.as_posix()))
        result = run_with_open_stdin([sys.executable, "-I", SCRIPT, "--fix-commit", fix, "--command", "true",
                                      "--cwd", self.repo / "sub"], env=self.env)
        self.git("config", "--unset", "core.fsmonitor")
        self.assertIsNotNone(result, "git waited for the input of the script")
        self.assertEqual(result[0], 0, result[2])
        self.assertIn("VERDICT: OTHER", result[1])

    def test_command_that_reads_input_gets_the_end_of_input(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        result = run_with_open_stdin([sys.executable, "-I", SCRIPT, "--fix-commit", fix, "--command", "cat",
                                      "--cwd", self.repo / "sub", "--timeout", "10"], env=self.env)
        self.assertIsNotNone(result, "the command waited for the input of the script")
        self.assertIn(": exit 0 after ", result[1])

    def test_worktree_of_the_user_that_moved_stays_listed(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        away = self.tmp / "away"
        self.git("worktree", "add", "-q", "-b", "side", away, "HEAD")
        shutil.move(away, self.tmp / "moved")
        args = [sys.executable, "-I", SCRIPT, "--fix-commit", fix, "--command", CHECK, "--cwd", self.repo / "sub"]
        self.assertResult(run(args, env=self.env, timeout=120), 0, "VERDICT: REGRESSION")
        self.assertIn("away", self.git("worktree", "list", "--porcelain"))
        self.assertEqual(list(self.temp.iterdir()), [])

    def test_worktree_whose_hook_fails_is_removed(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        hooks = self.tmp / "hooks"
        hooks.mkdir()
        (hooks / "post-checkout").write_bytes(b"#!/bin/sh\necho 'the hook says no' >&2\necho 'VERDICT: REGRESSION' >&2\n"
                                              b"printf '%0500d\\n' 7 >&2\nexit 1\n")
        os.chmod(hooks / "post-checkout", 0o755)
        self.git("config", "core.hooksPath", hooks.as_posix())
        out = self.check(fix)
        self.assertRegex(out, r"(?m)^RUN fix .* could not start: git worktree add failed: .*the hook says no "
                              r"VERDICT: REGRESSION 0+ \.\.\. \d+ more characters$")
        self.assertNotIn("RUN parent", out)
        self.assertRegex(out, r"RUN fix \w+ in temporary worktree ")
        self.assertNotIn("EXPORTED", out)
        self.assertNotIn("NO WORKTREE", out)
        self.assertEqual(re.findall(r"^VERDICT: .*$", out, re.M), ["VERDICT: OTHER"])

    def test_worktree_with_no_git_file_is_removed(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        out = self.check(fix, "rm -f ../.git; exit 1")
        self.assertEqual(out.count("REMOVED "), 2)
        self.assertNotIn("WARN", out)

    def test_rename_in_the_work_tree_is_one_changed_path(self):
        self.write("sub/aaa.txt", "x\n")
        self.commit("add")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        os.replace(self.repo / "sub/aaa.txt", self.repo / "sub/bbb.txt")
        self.git("add", "-N", "sub/bbb.txt")
        out = self.check(fix, "true")
        self.assertEqual(re.findall(r"^CHANGED: .*$", out, re.M), ["CHANGED: sub/bbb.txt"])

    def test_rename_in_the_index_is_one_changed_path(self):
        self.write("sub/aaa.txt", "x\n")
        self.commit("add")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.git("mv", "sub/aaa.txt", "sub/bbb.txt")
        out = self.check(fix, "true")
        self.assertEqual(re.findall(r"^CHANGED: .*$", out, re.M), ["CHANGED: sub/bbb.txt"])


def block_worktrees(repo):
    """Make git worktree add fail before it makes a folder, as the eval sandbox does (issue #232).

    A plain file in the place of .git/worktrees blocks it for each user, also for root, on Linux and on Windows.
    """
    (Path(repo) / ".git" / "worktrees").write_bytes(b"")


def can_make_links(folder):
    """True if this system can make a symbolic link in the folder. On Windows, that needs a right of the user."""
    link = Path(folder) / "link-probe"
    try:
        os.symlink("link-target", str(link))
    except OSError:
        return False
    link.unlink()
    return True


def snapshot(folder):
    """Each path below the folder, except .git, with its kind, its bytes or link target, and its executable bit."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames + [name for name in dirnames if Path(dirpath, name).is_symlink()]:
            path = Path(dirpath, name)
            rel = path.relative_to(folder).as_posix()
            if path.is_symlink():
                found[rel] = ("link", os.readlink(path).replace("\\", "/"))
            elif name != ".git":
                found[rel] = ("file", path.read_bytes(), os.name != "nt" and bool(path.stat().st_mode & 0o100))
    return found


class ExportTests(FailureCheckCase):
    """git worktree add fails and makes no folder, so the script runs the command in an export (issue #232)."""

    SAME = ("REASON: the command fails at both commits with the same exit code, the same error lines, "
            "and the same last lines after the first error line. "
            "With no error line, each line that is not blank and its count are the same.")
    FILES = (("target.txt", b"target text\nline two\n"), ("ignored.txt", b"not in an archive\n"),
             ("subst.txt", b"commit $Format:%H$\n"),
             (".gitattributes", b"ignored.txt export-ignore\nsubst.txt export-subst\n"),
             ("run.sh", b"#!/bin/sh\necho run\n"), ("my dir/a file.txt", b"one\ntwo\n"),
             ("link.txt", b"target.txt"), ("dir/up.txt", b"../target.txt"))
    MODES = {"run.sh": "100755", "link.txt": "120000", "dir/up.txt": "120000"}

    def test_blocked_worktree_gives_a_verdict_from_two_exports(self):
        self.write("sub/value.txt", "bad\n")
        self.commit("break")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        block_worktrees(self.repo)
        self.write(".bashrc", "# a stub of the sandbox\n")
        self.write(".gitconfig", "# a stub of the sandbox\n")
        out = self.check(fix)
        self.assertIn("CHANGED: .bashrc", out)
        self.assertRegex(out, r"RUN fix \w+ in temporary export .*review-loop-fc-\w+[/\\]fix[/\\]sub: exit 1 ")
        self.assertRegex(out, r"RUN parent \w+ in temporary export .*review-loop-fc-\w+[/\\]parent[/\\]sub: exit 1 ")
        self.assertEqual((out.count("EXPORTED "), out.count("REMOVED "), out.count("MADE ")), (2, 2, 0))
        self.assertEqual(len(re.findall(r"(?m)^NO WORKTREE: .+\nEXPORTED ", out)), 2)
        self.assertNotIn("WARN", out)
        self.assertTrue(out.endswith(f"VERDICT: SAME-AT-PARENT\n{self.SAME}\n"), out)

    def test_sandbox_stubs_do_not_change_the_verdict(self):
        self.write("sub/value.txt", "bad\n")
        self.commit("break")
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        block_worktrees(self.repo)
        clean = self.check(fix)
        self.assertIn("MAIN WORKTREE: clean", clean)
        self.write(".bashrc", "# a stub of the sandbox\n")
        stubs = self.check(fix)
        self.assertIn("MAIN WORKTREE: not clean", stubs)
        self.assertEqual((self.verdict(clean), self.verdict(stubs)), ("SAME-AT-PARENT", "SAME-AT-PARENT"))

    def test_blocked_worktree_runs_the_parent_in_an_export_after_the_main_worktree(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        block_worktrees(self.repo)
        out = self.check(fix)
        self.assertRegex(out, r"RUN fix \w+ in main worktree .*[/\\]repo[/\\]sub: exit 1 ")
        self.assertRegex(out, r"RUN parent \w+ in temporary export .*review-loop-fc-\w+[/\\]parent[/\\]sub: exit 0 ")
        self.assertEqual(self.verdict(out), "OTHER")
        self.assertIn("REASON: the command passes at the commit before the fix commit only in a temporary export", out)

    def test_blocked_worktree_gives_other_if_the_fix_passes_only_in_an_export(self):
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.write("dirty.txt", "x\n")
        block_worktrees(self.repo)
        out = self.check(fix)
        self.assertRegex(out, r"RUN fix \w+ in temporary export .*: exit 0 ")
        self.assertNotIn("RUN parent", out)
        self.assertEqual(self.verdict(out), "OTHER")
        self.assertIn("REASON: the command passes at the fix commit only in a temporary export", out)

    def assertExportFailed(self, out, error):
        """The fix run could not start, each error has its line, and the script printed one verdict."""
        self.assertRegex(out, r"(?m)^NO WORKTREE: .+\nEXPORTED ")
        self.assertRegex(out, r"(?m)^RUN fix \w+ in temporary export .*: could not start: git worktree add failed, "
                              r"and the export failed too: .*" + error)
        no_worktree = re.search(r"(?m)^NO WORKTREE: (.+)$", out).group(1)
        self.assertNotIn(no_worktree, re.search(r"(?m)^RUN fix .*$", out).group(), "the RUN line repeats the error")
        self.assertEqual((out.count("EXPORTED "), out.count("REMOVED ")), (1, 1))
        self.assertNotIn("RUN parent", out)
        self.assertEqual(re.findall(r"^VERDICT: .*$", out, re.M), ["VERDICT: OTHER"])
        self.assertTrue(out.endswith("REASON: the command did not run to an end at the fix commit.\n"), out)

    def test_export_that_cannot_write_a_file_gives_one_verdict_line(self):
        self.write("sub/other.txt", "fix\n")
        self.git("add", "-A")
        self.git("update-index", "--add", "--cacheinfo", "100644," + "12" * 20 + ",sub/missing.txt")
        tree = self.git("write-tree", "--missing-ok")
        fix = self.git("commit-tree", "-p", "HEAD", "-m", "fix", tree)
        self.git("update-ref", "HEAD", fix)
        block_worktrees(self.repo)
        self.assertExportFailed(self.check(fix), r"missing\.txt")

    def test_export_that_cannot_read_the_tree_gives_one_verdict_line(self):
        text = (f"tree {'34' * 20}\nparent {self.base}\n"
                "author t <t@example.com> 0 +0000\ncommitter t <t@example.com> 0 +0000\n\nfix\n")
        fix = run(["git", "-C", self.repo, "hash-object", "-t", "commit", "-w", "--stdin"], stdin=text.encode(),
                  text=False, check=True).stdout.decode().strip()
        block_worktrees(self.repo)
        self.assertExportFailed(self.check(fix), fix)

    def test_export_has_the_files_of_a_worktree(self):
        for path, data in self.FILES:
            blob = run(["git", "-C", self.repo, "hash-object", "-w", "--stdin"], stdin=data, text=False,
                       check=True).stdout.decode().strip()
            self.git("update-index", "--add", "--cacheinfo", f"{self.MODES.get(path, '100644')},{blob},{path}")
        self.git("commit", "-q", "-m", "fix")
        fix = self.git("rev-parse", "HEAD")
        links = can_make_links(self.tmp)
        for symlinks, autocrlf in (("true", "true"), ("false", "true"), ("true", "false"), ("false", "false")):
            with self.subTest(symlinks=symlinks, autocrlf=autocrlf):
                if symlinks == "true" and not links:
                    continue
                self.git("config", "core.symlinks", symlinks)
                self.git("config", "core.autocrlf", autocrlf)
                reference = self.tmp / "reference"
                self.git("worktree", "add", "-q", "--detach", reference, fix)
                expected = snapshot(reference)
                self.git("worktree", "remove", "--force", reference)
                index = (self.repo / ".git" / "index").read_bytes()
                git_files = sorted(path for path in (self.repo / ".git").rglob("*") if path.is_file())
                status = self.git("status", "--porcelain", "--untracked-files=all")
                trees = fc.Worktrees(self.repo)
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        path, err = trees.export("fix", fix)
                    self.assertIsNone(err)
                    self.assertEqual(snapshot(path), expected)
                    self.assertIn("link.txt", expected)
                    self.assertFalse((path / ".git").exists(), "the export holds git data")
                finally:
                    with contextlib.redirect_stdout(io.StringIO()):
                        trees.remove()
                self.assertEqual((self.repo / ".git" / "index").read_bytes(), index, "the export changed the index")
                self.assertEqual(sorted(path for path in (self.repo / ".git").rglob("*") if path.is_file()), git_files)
                self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), status,
                                 "the export changed the main worktree")

    def export_of(self, name, sha, trees):
        with contextlib.redirect_stdout(io.StringIO()):
            path, err = trees.export(name, sha)
        self.assertIsNone(err)
        return path

    def test_export_takes_the_attributes_of_its_commit(self):
        self.git("config", "core.autocrlf", "false")
        self.write("a.txt", "one\ntwo\n")
        parent = self.commit("parent")
        self.write(".gitattributes", "*.txt text eol=crlf\n")
        fix = self.commit("fix")
        for name, sha, expected in (("parent", parent, b"one\ntwo\n"), ("fix", fix, b"one\r\ntwo\r\n")):
            with self.subTest(commit=name):
                trees = fc.Worktrees(self.repo)
                try:
                    path = self.export_of(name, sha, trees)
                    self.assertEqual((path / "a.txt").read_bytes(), expected)
                finally:
                    with contextlib.redirect_stdout(io.StringIO()):
                        trees.remove()

    def test_export_does_not_read_an_attributes_file_that_is_not_committed(self):
        self.git("config", "core.autocrlf", "false")
        self.write("a.txt", "one\ntwo\n")
        fix = self.commit("fix")
        self.write(".gitattributes", "*.txt text eol=crlf\n")
        trees = fc.Worktrees(self.repo)
        try:
            path = self.export_of("fix", fix, trees)
            self.assertEqual((path / "a.txt").read_bytes(), b"one\ntwo\n")
        finally:
            with contextlib.redirect_stdout(io.StringIO()):
                trees.remove()

    def test_command_in_an_export_finds_no_repository_above_the_temporary_folder(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("dirty.txt", "x\n")
        block_worktrees(self.repo)
        temp = git_init(self.tmp / "outer") / "temp"
        temp.mkdir()
        env = clean_env(TMPDIR=str(temp), TEMP=str(temp), TMP=str(temp))
        command = "git rev-parse --git-dir > /dev/null 2>&1 && echo found-a-repository; echo error: stop; exit 1"
        out = self.check(fix, command, env=env)
        self.assertEqual(out.count(" in temporary export "), 2)
        self.assertNotIn("found-a-repository", out)
        self.assertEqual(list(temp.iterdir()), [], "a temporary folder is left")

    def test_read_only_file_of_the_command_does_not_keep_the_export(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        block_worktrees(self.repo)
        out = self.check(fix, "echo x > made.txt && chmod 444 made.txt && " + CHECK)
        self.assertEqual((out.count("EXPORTED "), out.count("REMOVED "), out.count("WARN")), (1, 1, 0))

    @unittest.skipUnless(os.name == "nt", "only Windows keeps a read-only link")
    def test_delete_tree_deletes_a_read_only_link(self):
        tree = self.tmp / "tree"
        tree.mkdir()
        if not can_make_links(tree):
            self.skipTest("this user cannot make links")
        target = self.tmp / "target.txt"
        target.write_text("keep\n")
        os.chmod(target, stat.S_IREAD)
        self.addCleanup(os.chmod, target, stat.S_IWRITE)
        os.symlink(target, tree / "link")
        os.chmod(tree / "link", stat.S_IREAD, follow_symlinks=False)
        fc.delete_tree(tree)
        self.assertFalse(tree.exists(), "the read-only link keeps the folder")
        self.assertFalse(os.access(target, os.W_OK), "the target becomes writable")

    @unittest.skipIf(os.name == "nt", "a read-only folder does not keep a file on Windows")
    def test_delete_keeps_the_mode_of_a_folder_outside_the_run(self):
        prefix = []
        if os.geteuid() == 0:
            capsh = shutil.which("capsh")
            if not capsh:
                self.skipTest("root deletes a read-only folder")
            prefix = [capsh, "--drop=cap_dac_override,cap_dac_read_search", "--", "-c", 'exec "$0" "$@"']
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("dirty.txt", "x\n")
        block_worktrees(self.repo)
        outside = self.tmp / "outside"
        outside.mkdir()
        os.chmod(outside, 0o755)
        self.addCleanup(os.chmod, outside, 0o755)
        command = f"mkdir cache && ln -s {shlex.quote(outside.as_posix())} cache/data && chmod 555 cache && " + CHECK
        try:
            out = run(prefix + [sys.executable, "-I", SCRIPT, "--fix-commit", fix, "--command", command, "--cwd",
                                self.repo / "sub"], env=self.env, timeout=120).stdout
        finally:
            run(["chmod", "-R", "u+rwx", self.temp])
        self.assertEqual(oct(stat.S_IMODE(outside.stat().st_mode)), oct(0o755))
        self.assertIn("WARN: could not delete the folder", out)
        self.assertNotIn("REMOVED", out)

    def test_command_in_an_export_keeps_the_ceiling_of_the_caller(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("dirty.txt", "x\n")
        block_worktrees(self.repo)
        keep = str(self.tmp / "keep-me")
        env = dict(self.env, GIT_CEILING_DIRECTORIES=keep)
        out = self.check(fix, 'echo "error: ceiling $GIT_CEILING_DIRECTORIES"; exit 1', env=env)
        self.assertRegex(out, r"RUN fix \w+ in temporary export .*\n  ERROR \| error: ceiling \S*review-loop-fc-\w+"
                         + re.escape(os.pathsep + keep) + "\n")

    def test_export_gets_the_git_settings_of_the_environment(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("dirty.txt", "x\n")
        block_worktrees(self.repo)
        env = dict(self.env, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.autocrlf", GIT_CONFIG_VALUE_0="true")
        out = self.check(fix, 'echo "error: value.txt has $(wc -c < value.txt) bytes"; exit 1', env=env)
        self.assertRegex(out, r"RUN fix \w+ in temporary export .*\n  ERROR \| error: value\.txt has +5 bytes")


class UsageTests(FailureCheckCase):
    def test_root_commit_has_no_parent(self):
        result = run([sys.executable, "-I", SCRIPT, "--fix-commit", self.base, "--command", "true",
                      "--cwd", self.repo], env=self.env)
        self.assertResult(result, 2, "has no parent commit")

    def test_shallow_clone_without_the_parent_commit_is_named(self):
        self.write("sub/value.txt", "bad\n")
        self.commit("fix")
        clone = self.tmp / "shallow"
        run(["git", "clone", "-q", "--depth", "1", self.repo.as_uri(), clone], check=True)
        result = run([sys.executable, "-I", SCRIPT, "--fix-commit", "HEAD", "--command", "true", "--cwd", clone],
                     env=self.env)
        self.assertResult(result, 2, "shallow clone")

    def test_unknown_commit_and_option_like_commit_are_refused(self):
        for fix, text in (("no-such-commit", "is not a commit"), ("--output=x", "must not start with '-'")):
            result = run([sys.executable, "-I", SCRIPT, "--fix-commit=" + fix, "--command", "true",
                          "--cwd", self.repo], env=self.env)
            self.assertResult(result, 2, text)

    def test_temporary_folder_inside_the_repository_is_refused(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        inside = self.repo / "tmp"
        inside.mkdir()
        env = clean_env(TMPDIR=str(inside), TEMP=str(inside), TMP=str(inside))
        result = run([sys.executable, "-I", SCRIPT, "--fix-commit", fix, "--command", "true",
                      "--cwd", self.repo], env=env)
        self.assertResult(result, 2, "is inside the repository")
        self.assertEqual(list(inside.iterdir()), [])

    def test_folder_in_no_repository_is_refused(self):
        result = run([sys.executable, "-I", SCRIPT, "--fix-commit", "HEAD", "--command", "true",
                      "--cwd", self.temp], env=self.env)
        self.assertResult(result, 2, "error: git rev-parse failed: ")

    def test_folder_outside_the_work_tree_is_refused(self):
        env = dict(self.env, GIT_DIR=str(self.repo / ".git"), GIT_WORK_TREE=str(self.repo))
        result = run([sys.executable, "-I", SCRIPT, "--fix-commit", "HEAD", "--command", "true",
                      "--cwd", self.temp], env=env)
        self.assertResult(result, 2, "is not inside the work tree")

    def test_time_limit_that_is_not_positive_is_refused(self):
        for seconds in ("0", "-5"):
            result = run([sys.executable, "-I", SCRIPT, "--fix-commit", "HEAD", "--command", "true",
                          "--cwd", self.repo, "--timeout", seconds], env=self.env)
            self.assertResult(result, 2, "--timeout must be a positive number of seconds")


class UnitTests(unittest.TestCase):
    def test_signature_ignores_folders_times_and_addresses(self):
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["FAIL test_x (12.3 s) at 0x7ffd12 in /work/repo/src/a.py"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["FAIL test_x (9 s) at 0x1 in /tmp/review-loop-fc-ab12/parent/src/a.py"]
        self.assertEqual(a.signature({"/work/repo"}), b.signature({"/work/repo"}))
        self.assertEqual(len(a.signature({"/work/repo"})), 1)

    def test_signature_ignores_the_text_before_a_folder(self):
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["a.cs(5,6): error CS0246 [/work/repo/a.csproj]", "at f (file:///work/repo/x.mjs:4:31)"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["a.cs(5,6): error CS0246 [/tmp/review-loop-fc-ab12/parent/a.csproj]",
                   "at f (file:///tmp/review-loop-fc-ab12/parent/x.mjs:4:31)"]
        self.assertEqual(a.signature({"/work/repo"}), b.signature({"/work/repo"}))

    def test_signature_ignores_a_space_in_the_folder(self):
        roots = fc.path_forms(Path("/work/my repo")) | fc.path_forms(Path("/tmp/my tmp/review-loop-fc-ab12/parent"))
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["error at /work/my repo/t.py:9", "Error at f (file:///work/my%20repo/x.mjs:4:31)"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["error at /tmp/my tmp/review-loop-fc-ab12/parent/t.py:9",
                   "Error at f (file:///tmp/my%20tmp/review-loop-fc-ab12/parent/x.mjs:4:31)"]
        self.assertEqual(a.signature(roots), b.signature(roots))
        self.assertEqual(len(a.signature(roots)), 2)

    def test_signature_ignores_the_duration_of_node_test(self):
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["# fail 1", "# duration_ms 85.2958"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["# fail 1", "# duration_ms 90.1112"]
        self.assertEqual(a.signature(set()), b.signature(set()))

    def test_signature_of_a_long_line_is_fast(self):
        for line in ("AssertionError: " + "A" * 100_000, "error " + "review-loop-fc-" * 14_000,
                     "error " + "1 passed, " * 10_000, "== error " + "Passed: " * 12_500,
                     "error " + "\x1b[" * 30_000):
            a = fc.Run("fix", "a" * 40, "x", "main")
            a.lines = [line]
            start = time.monotonic()
            a.signature({"/work/repo", "C:\\work\\repo"})
            self.assertLess(time.monotonic() - start, 5, line[:30])

    def test_signature_ignores_the_clock_time(self):
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["[10:15:01] error: boom"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["[9:07:59.250] error: boom"]
        self.assertEqual(a.signature(set()), b.signature(set()))

    def test_signature_takes_the_longest_root_first(self):
        roots = ["/tmp/re", "/tmp/review-loop-fc-ab12/parent"]
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["error at /tmp/re/t.py:9"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["error at /tmp/review-loop-fc-ab12/parent/t.py:9"]
        self.assertEqual(a.signature(roots), b.signature(roots))
        self.assertEqual(a.signature(roots[::-1]), b.signature(roots[::-1]))

    def test_path_with_a_character_that_is_not_printable_is_shown_as_json(self):
        self.assertEqual(fc.show("a\nb.py"), '"a\\nb.py"')
        self.assertEqual(fc.show("a b\u00e9.py"), "a b\u00e9.py")

    def test_line_is_cut_only_over_the_limit(self):
        self.assertEqual(fc.cut("x" * fc.LINE_CHARS), "x" * fc.LINE_CHARS)
        self.assertEqual(fc.cut("x" * fc.LINE_CHARS + "yz"), "x" * fc.LINE_CHARS + " ... 2 more characters")

    def test_lines_before_the_first_error_line_do_not_count(self):
        a = fc.Run("fix", "a" * 40, "x", "main")
        a.lines = ["  All projects are up-to-date for restore.", "a.cs(5,6): error CS0246"]
        b = fc.Run("parent", "b" * 40, "y", "temp")
        b.lines = ["  Restored /tmp/a.csproj (in 191 ms).", "a.cs(5,6): error CS0246"]
        self.assertEqual(a.signature(set()), b.signature(set()))

    def lint_verdict(self, fix_lines, parent_lines, roots=(), fix_where="main worktree", parent_where="temporary worktree"):
        """The verdict for a lint that fails with exit code 1 at both commits and prints the given lines."""
        fix = fc.Run("fix", "a" * 40, "x", fix_where)
        fix.code, fix.lines = 1, fix_lines
        parent = fc.Run("parent", "b" * 40, "y", parent_where)
        parent.code, parent.lines = 1, parent_lines
        return fc.verdict(False, fix, parent, set(roots))[0]

    def test_same_lint_output_with_no_error_word_is_same_at_parent(self):
        hit = "src/a.py:1:1: F401 'os' imported but unused"
        self.assertEqual(self.lint_verdict([hit, "Done in 0.31s"], [hit, "Done in 1.02s"]), "SAME-AT-PARENT")

    def test_new_lint_hit_between_the_first_and_the_last_lines_is_other(self):
        hits = [f"src/m{i:03}.py:1:1: F401 'os' imported but unused" for i in range(400)]
        new = "src/m199a.py:3:1: E302 expected 2 blank lines, found 1"
        self.assertEqual(self.lint_verdict([*hits[:200], new, *hits[200:]], hits), "OTHER")

    def test_new_lint_hit_in_the_middle_of_a_short_output_is_other(self):
        hits = [f"src/m{i:02}.py:1:1: F401 'os' imported but unused" for i in range(30)]
        new = "src/new.py:3:1: E302 expected 2 blank lines, found 1"
        self.assertEqual(self.lint_verdict([*hits[:15], new, *hits[15:]], hits), "OTHER")

    def test_other_lint_output_with_the_same_line_count_is_other(self):
        self.assertEqual(self.lint_verdict(["src/a.py:1:1: F401 'os' imported but unused"],
                                           ["src/b.py:3:1: E302 expected 2 blank lines, found 1"]), "OTHER")

    def test_other_first_lint_hit_with_the_same_other_lines_is_other(self):
        rest = ["src/b.py:3:1: E302 expected 2 blank lines, found 1", "Done in 0.31s"]
        self.assertEqual(self.lint_verdict(["src/a.py:9:1: F401 'os' imported but unused", *rest],
                                           ["src/a.py:1:1: F401 'os' imported but unused", *rest]), "OTHER")

    def test_second_lint_hit_with_the_text_of_a_hit_of_another_file_is_other(self):
        doc_start = '  1:1       warning  missing document start "---"  (document-start)'
        truthy = "  3:5       warning  truthy value should be one of [false, true]  (truthy)"
        parent = ["a.yaml", truthy, "", "b.yaml", doc_start, ""]
        self.assertEqual(self.lint_verdict(["a.yaml", doc_start, truthy, "", "b.yaml", doc_start, ""], parent), "OTHER")
        self.assertEqual(self.lint_verdict(parent[3:] + parent[:3], parent), "SAME-AT-PARENT")

    def test_blank_lines_with_no_error_line_do_not_count(self):
        hit = "src/a.py:1:1: F401 'os' imported but unused"
        self.assertEqual(self.lint_verdict([""], ["", "", ""]), "OTHER")
        self.assertEqual(self.lint_verdict(["", "  \t"], ["", "  \t"]), "OTHER")
        self.assertEqual(self.lint_verdict([hit, "", ""], ["", hit]), "SAME-AT-PARENT")

    def test_output_with_no_line_to_compare_says_so(self):
        fix = fc.Run("fix", "a" * 40, "x", "main worktree")
        fix.code, fix.lines = 1, ["", "  "]
        parent = fc.Run("parent", "b" * 40, "y", "temporary worktree")
        parent.code, parent.lines = 1, ["", "  "]
        token, reason = fc.verdict(False, fix, parent, set())
        self.assertEqual(token, "OTHER")
        self.assertIn("has no line to compare", reason)

    def test_error_line_at_only_one_commit_is_other(self):
        hits = [f"src/m{i:02}.py:1:1: F401 'os' imported but unused" for i in range(15)]
        new = "src/a_new.py:3:1: E302 expected 2 blank lines, found 1"
        roots = ["/work/errors/repo", "/tmp/review-loop-fc-ab12/parent"]
        self.assertEqual(self.lint_verdict(["Linting /work/errors/repo", new, *hits],
                                           ["Linting /tmp/review-loop-fc-ab12/parent", *hits], roots), "OTHER")

    def test_lines_between_an_error_on_the_first_line_and_the_last_lines_do_not_count(self):
        tail = [f"step {i}" for i in range(15)]
        self.assertEqual(self.lint_verdict(["error: boom", "compiling a.py", *tail],
                                           ["error: boom", "compiling b.py", *tail]), "SAME-AT-PARENT")

    def test_error_line_above_the_last_lines_counts_and_another_line_there_does_not(self):
        def signature(error, changed=None):
            run = fc.Run("fix", "a" * 40, "x", "main")
            run.lines = [error, *(f"line {i}" for i in range(20))]
            if changed is not None:
                run.lines[changed] = "another line"
            return run.signature(set())

        # The output has 21 lines, so the last 15 lines start at index 6.
        self.assertNotEqual(signature("error: a"), signature("error: b"))
        self.assertEqual(signature("error: a", changed=5), signature("error: a"))
        self.assertNotEqual(signature("error: a", changed=6), signature("error: a"))

    def test_swapped_hit_above_the_only_error_word_is_other(self):
        def full(name):
            return [f"F401 [*] `{name}` imported but unused", " --> src\\a.py:1:8", "  |", f"1 | import {name}",
                    "  |        " + "^" * len(name), f"help: Remove unused import: `{name}`", "  |",
                    f"  - import {name}", "  |", "", "Found 1 error.", "[*] 1 fixable with `--fix`."]

        self.assertEqual(self.lint_verdict(ruff_concise(RUFF_SYS), ruff_concise(RUFF_OS)), "OTHER")
        self.assertEqual(self.lint_verdict(full("sys"), full("os")), "OTHER")
        self.assertEqual(self.lint_verdict(full("os"), full("os")), "SAME-AT-PARENT")

    def test_swapped_hit_above_an_error_word_in_a_file_name_is_other(self):
        fix, parent = ruff_concise(RUFF_SYS, RUFF_JSON), ruff_concise(RUFF_OS, RUFF_JSON)
        self.assertEqual(self.lint_verdict(fix, parent), "OTHER")

    def test_swapped_hit_above_a_summary_with_an_error_word_is_other(self):
        def stylish(hit):
            return ["/work/src/a.js", hit, "", "✖ 1 problem (0 errors, 1 warning)"]

        unused = "  3:5  warning  'x' is assigned a value but never used  no-unused-vars"
        console = "  7:1  warning  Unexpected console statement  no-console"
        self.assertEqual(self.lint_verdict(stylish(unused), stylish(console)), "OTHER")

    def test_moved_hit_above_a_summary_with_an_error_word_is_same_at_parent(self):
        def grouped(place):
            return ["src\\a.py:", f"  {place} F401 [*] `os` imported but unused", "", "Found 1 error.",
                    "[*] 1 fixable with `--fix`."]

        self.assertEqual(self.lint_verdict(grouped("2:8"), grouped("1:8")), "SAME-AT-PARENT")
        warning = "a.cs({},13): warning CS0168: The variable 'x' is declared but never used"
        self.assertEqual(self.lint_verdict([warning.format(4), "Build FAILED."], [warning.format(3), "Build FAILED."]),
                         "SAME-AT-PARENT")
        self.assertEqual(self.lint_verdict(["src/a.py:4:9: note: x", "1 error"], ["src/a.py:3:5: note: x", "1 error"]),
                         "SAME-AT-PARENT")
        self.assertEqual(self.lint_verdict(["a.py:4:9: E501 x", "1 error"], ["a.py:3:5: E501 x", "1 error"]),
                         "SAME-AT-PARENT")
        roots = ["/work/repo", "/tmp/review-loop-fc-ab12/parent"]
        stylish = ["{}/src/a.js", "  {}  warning  'x' is assigned a value but never used  no-unused-vars", "",
                   "x 1 problem (0 errors, 1 warning)"]
        fix = [stylish[0].format(roots[0]), stylish[1].format("14:5"), *stylish[2:]]
        parent = [stylish[0].format(roots[1]), stylish[1].format("3:5"), *stylish[2:]]
        self.assertEqual(self.lint_verdict(fix, parent, roots), "SAME-AT-PARENT")

    def test_same_hit_swapped_into_another_file_is_other(self):
        def grouped(file):
            return [f"src\\{file}:", "  1:8 F401 [*] `os` imported but unused", "", "Found 1 error.",
                    "[*] 1 fixable with `--fix`."]

        self.assertEqual(self.lint_verdict(grouped("b.py"), grouped("a.py")), "OTHER")
        self.assertEqual(self.lint_verdict(grouped("v2\\a.py"), grouped("v3\\a.py")), "OTHER")
        self.assertEqual(self.lint_verdict(grouped("a.py"), grouped("a.py")), "SAME-AT-PARENT")

    def test_same_hit_swapped_into_another_file_of_the_root_folder_is_other(self):
        def grouped(file):
            return [f"{file}:", "  1:8 F401 [*] `os` imported but unused", "", "Found 1 error.",
                    "[*] 1 fixable with `--fix`."]

        self.assertEqual(self.lint_verdict(grouped("b.py"), grouped("a.py")), "OTHER")
        self.assertEqual(self.lint_verdict(grouped("a.py"), grouped("a.py")), "SAME-AT-PARENT")
        for fix, parent in (("1-intro.py", "2-intro.py"), ("01-intro/main.py", "02-intro/main.py"),
                            ("01-intro\\main.py", "02-intro\\main.py"), ("1+a.py", "2+a.py")):
            with self.subTest(fix=fix):
                self.assertEqual(self.lint_verdict(grouped(fix), grouped(parent)), "OTHER")

    def test_line_of_test_dots_is_not_a_path(self):
        self.assertEqual(self.lint_verdict(["..F", "FAIL: test_x"], [".F", "FAIL: test_x"]), "SAME-AT-PARENT")

    def test_time_above_the_error_line_is_not_a_place(self):
        lines = {"tqdm": ("100%|##########| 10/10 [00:03<00:00,  3.21it/s]",
                          "100%|##########| 10/10 [00:02<00:00,  4.02it/s]"),
                 "isoformat": ("start 2026-11-20T10:31:05.123456+00:00", "start 2026-11-20T10:30:59.654321+00:00")}
        for name, (fix, parent) in lines.items():
            with self.subTest(name=name):
                self.assertEqual(self.lint_verdict([fix, "error: x"], [parent, "error: x"]), "SAME-AT-PARENT")

    def test_error_line_that_comes_one_more_time_is_other(self):
        error = "error: the docs theme is missing."
        self.assertEqual(self.lint_verdict([error, error], [error]), "OTHER")
        self.assertEqual(self.lint_verdict([error] * 3, [error] * 2), "OTHER")

    def test_root_counts_only_at_the_start_of_a_path(self):
        def mypy(path):
            return [f'{path}:3: error: Name "x" is not defined  [name-defined]',
                    "Found 1 error in 1 file (checked 2 source files)"]

        self.assertEqual(self.lint_verdict(mypy("src/app/util.py"), mypy("tests/app/util.py"), ["/app"]), "OTHER")
        for start in ("error in -I", "error in --out=", "error: no file '"):
            with self.subTest(start=start):
                parent = [start + "/tmp/review-loop-fc-ab12/parent/b.c"]
                self.assertEqual(self.lint_verdict([start + "/app/b.c"], parent, ["/app"]), "SAME-AT-PARENT")
        windows = fc.path_forms(PureWindowsPath("C:\\work\\repo"))
        self.assertEqual(self.lint_verdict(["Error at f (file:///C:/work/repo/x.mjs:4:31)"],
                                           ["Error at f (file:///C:/Temp/review-loop-fc-ab12/parent/x.mjs:4:31)"],
                                           windows), "SAME-AT-PARENT")

    def test_swapped_file_of_a_python_syntax_error_is_other(self):
        # The output of `python -m py_compile <path>` of Python 3.15.0.
        def syntax_error(path, line):
            return [f'  File "{path}", line {line}', "    x = = 1", "        ^", "SyntaxError: invalid syntax"]

        self.assertEqual(self.lint_verdict(syntax_error("src/a.py", 2), syntax_error("src/b.py", 2)), "OTHER")
        self.assertEqual(self.lint_verdict(syntax_error("src/a.py", 9), syntax_error("src/a.py", 2)), "SAME-AT-PARENT")

    def test_root_after_a_character_that_is_not_of_a_file_name_is_a_token(self):
        roots = ["/work/repo", "/tmp/review-loop-fc-ab12/parent"]
        for form in ("error:{}/a.py:3", "error: PYTHONPATH={}/src:{}/lib", "error: ld -Wl,-rpath,{}/lib failed",
                     "error: failed to parse manifest at `{}/Cargo.toml`", "error: cannot read @{}/args.rsp",
                     "IOException: URL [file:{}/target/app.xml]"):
            with self.subTest(form=form):
                fix, parent = form.replace("{}", roots[0]), form.replace("{}", roots[1])
                self.assertEqual(self.lint_verdict([fix], [parent], roots), "SAME-AT-PARENT")
                self.assertEqual(self.lint_verdict([fix], [parent], roots[:1]), "SAME-AT-PARENT")
        windows = fc.path_forms(PureWindowsPath("C:\\work\\repo"))
        self.assertEqual(self.lint_verdict(["IOException: file:/C:/work/repo/a.xml"],
                                           ["IOException: file:/C:/Temp/review-loop-fc-ab12/parent/a.xml"], windows),
                         "SAME-AT-PARENT")

    def test_text_before_the_temporary_folder_stays(self):
        self.assertEqual(self.lint_verdict(["x.c:3:error:/tmp/review-loop-fc-ab12/fix/inc/a.h"],
                                           ["y.c:9:error:/tmp/review-loop-fc-ab12/parent/inc/a.h"]), "OTHER")

    def test_place_with_no_extension_and_place_of_maven_count(self):
        for form in ("Makefile:3: warning: overriding recipe for target '{}'",
                     "Gemfile:3:1: C: Style/{}: x", "[WARNING] /w/A.java:[3,5] {}"):
            with self.subTest(form=form):
                self.assertEqual(self.lint_verdict([form.format("a"), "1 error"], [form.format("b"), "1 error"]),
                                 "OTHER")
        for fix, parent in (("listening on localhost:54321", "connected to localhost:54321"),
                            ("listening on 127.0.0.1:54321", "connected to 127.0.0.1:54321"),
                            ('{"level":3,"msg":"a"}', '{"level":3,"msg":"b"}')):
            with self.subTest(fix=fix):
                self.assertEqual(self.lint_verdict([fix, "1 error"], [parent, "1 error"]), "SAME-AT-PARENT")

    def test_moved_place_of_maven_is_same_at_parent(self):
        form = "[WARNING] /w/A.java:[{}] unchecked call"
        self.assertEqual(self.lint_verdict([form.format("4,7"), "1 error"], [form.format("3,5"), "1 error"]),
                         "SAME-AT-PARENT")

    def test_run_with_an_error_word_only_in_its_root_never_matches_a_run_with_none(self):
        roots = ["/work/errors/repo", "/tmp/review-loop-fc-ab12/parent"]
        fix = ["new line from the fix", "cannot read /work/errors/repo/a.txt"]
        parent = ["cannot read /tmp/review-loop-fc-ab12/parent/a.txt"]
        self.assertEqual(self.lint_verdict(fix, parent, roots), "OTHER")

    def test_run_with_an_error_line_never_matches_a_run_with_none(self):
        roots = ["/work/errors/repo", "/tmp/review-loop-fc-ab12/parent"]
        hit = "src/a.py:1:1: F401 'os' imported but unused"
        self.assertEqual(self.lint_verdict(["Linting /work/errors/repo", hit],
                                           ["Linting /tmp/review-loop-fc-ab12/parent", hit], roots), "OTHER")

    def test_place_with_color_codes_counts(self):
        def hit(message):
            return [f"\x1b[1msrc/a.py\x1b[0m:\x1b[36m3\x1b[0m:5: {message}", "Found 1 error."]

        self.assertEqual(self.lint_verdict(hit("unused variable"), hit("unused import")), "OTHER")

    def test_place_between_the_first_error_line_and_the_last_lines_counts(self):
        tail = [f"step {i}" for i in range(15)]
        self.assertEqual(self.lint_verdict(["error: boom", "src/a.py:3: note: y", *tail],
                                           ["error: boom", "src/a.py:3: note: x", *tail]), "OTHER")

    def test_more_forms_of_a_place_count(self):
        for form in ("a.cs(3,6,5,10): warning {}", "    3 |   int {};", "3  |     let {} = 5;",
                     "SRC/A.PY:3: {}", "3:5  warning  {}"):
            with self.subTest(form=form):
                self.assertEqual(self.lint_verdict([form.format("x"), "1 error"], [form.format("y"), "1 error"]),
                                 "OTHER")

    def test_reason_of_other_names_the_lines_with_a_place(self):
        fix = fc.Run("fix", "a" * 40, "x", "main worktree")
        fix.code, fix.lines = 1, ["src/a.py:3: note: x", "1 error"]
        parent = fc.Run("parent", "b" * 40, "y", "temporary worktree")
        parent.code, parent.lines = 1, ["src/b.py:3: note: x", "1 error"]
        token, reason = fc.verdict(False, fix, parent, set())
        self.assertEqual(token, "OTHER")
        self.assertIn("the lines that name a place", reason)

    def test_digit_of_a_file_name_in_a_line_with_only_a_path_stays(self):
        def stylish(file):
            return [file, "  3:5  warning  'x' is assigned a value but never used  no-unused-vars", "",
                    "x 1 problem (0 errors, 1 warning)"]

        for fix, parent in (("/w/src/step-1-a.js", "/w/src/step-2-a.js"), ("/w/src/2-a.js", "/w/src/3-a.js"),
                            ("/w/src/a.2-b.js", "/w/src/a.3-b.js"), ("/w/src/a-2.js", "/w/src/a-3.js"),
                            ("/w/a-2/x.js", "/w/a-3/x.js"), ("/w/src/2/a.js", "/w/src/3/a.js"),
                            ("/w/src/a,2.js", "/w/src/a,3.js"), ("/w/src/a,2b.js", "/w/src/a,3b.js"),
                            ("/w/src/a,2/x.js", "/w/src/a,3/x.js"), ("/w/a,2\\x.js", "/w/a,3\\x.js")):
            with self.subTest(fix=fix):
                self.assertEqual(self.lint_verdict(stylish(fix), stylish(parent)), "OTHER")
        self.assertEqual(self.lint_verdict(stylish("/w/_posts/2024-01-15-a.js"), stylish("/w/_posts/2024-02-15-a.js")),
                         "OTHER")
        python = ['  File "src/step-{}-a.py", line 2', "    x = = 1", "SyntaxError: invalid syntax"]
        self.assertEqual(self.lint_verdict([python[0].format(1), *python[1:]], [python[0].format(2), *python[1:]]),
                         "OTHER")

    def test_number_in_the_message_of_a_place_line_stays(self):
        for fix, parent in (("src/a.py:3:1: W1 call f(1) is slow", "src/a.py:3:1: W1 call f(2) is slow"),
                            ("src/a.py:3:1: W1 ratio 3:4", "src/a.py:3:1: W1 ratio 3:5"),
                            ("3 |     let x = foo(1);", "3 |     let x = foo(2);")):
            with self.subTest(fix=fix):
                self.assertEqual(self.lint_verdict([fix, "1 error"], [parent, "1 error"]), "OTHER")

    def test_signature_of_a_long_line_with_an_option_or_a_path_is_fast(self):
        for lines in (["-a" + "a" * 100_000], ["error in -I" + "a-" * 50_000], ["-a" + "a" * 100_000, "error: x"],
                      ["a/" * 50_000 + "a.py", "error: x"], ['File "' * 20_000, "error: x"],
                      ["a." + "a" * 100_000, "error: x"], ["a." * 50_000, "error: x"]):
            a = fc.Run("fix", "a" * 40, "x", "main")
            a.lines = lines
            start = time.monotonic()
            a.signature({"/work/repo", "C:\\work\\repo"})
            self.assertLess(time.monotonic() - start, 5, lines[0][:30])

    def test_same_lint_output_with_the_folder_of_each_run_is_same_at_parent(self):
        hit = "/src/a.py:1:1: F401 'os' imported but unused"
        roots = ["/work/repo", "/tmp/review-loop-fc-ab12/parent"]
        self.assertEqual(self.lint_verdict(["/work/repo" + hit], ["/tmp/review-loop-fc-ab12/parent" + hit], roots),
                         "SAME-AT-PARENT")

    def test_place_of_a_lint_hit_is_not_a_clock_time(self):
        self.assertEqual(self.lint_verdict(["prog.1:12:10: bad macro"], ["prog.1:34:56: bad macro"]), "OTHER")
        self.assertEqual(self.lint_verdict(["a.py:12:10:15: x"], ["a.py:34:56:15: x"]), "OTHER")
        self.assertEqual(self.lint_verdict(["a.py:1:1: x", "at 10:15:01"], ["a.py:1:1: x", "at 9:07:59.250"]),
                         "SAME-AT-PARENT")

    def test_lint_with_no_error_line_in_a_temporary_export_is_other(self):
        hit = "src/a.py:1:1: F401 'os' imported but unused"
        self.assertEqual(self.lint_verdict([hit], [hit], parent_where="temporary export"), "OTHER")
        self.assertEqual(self.lint_verdict([hit], [hit], fix_where="temporary export"), "OTHER")
        error = "fatal: not a git repository"
        self.assertEqual(self.lint_verdict(["error: x", error], ["error: x", error], parent_where="temporary export"),
                         "SAME-AT-PARENT")

    def test_error_rule_matches_class_names_and_plural_forms(self):
        for line in ("KeyError: 'x'", "System.InvalidOperationException: y", "3 exceptions", "test_x fails"):
            self.assertTrue(fc.ERROR.search(line), line)

    def test_output_survives_a_path_that_is_not_utf8(self):
        raw = io.BytesIO()
        out = io.TextIOWrapper(raw, encoding="ascii", newline="\n")
        with (mock.patch.object(fc, "check", lambda args, bash: print("CHANGED: a\udcffb\u00e9")),
              mock.patch.object(fc, "find_bash", lambda: "bash"),
              mock.patch.object(signal, "signal"),
              mock.patch.object(sys, "stdout", out),
              mock.patch.object(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="ascii"))):
            code = fc.main(["--fix-commit", "x", "--command", "y"])
        out.flush()
        self.assertEqual(code, 0)
        self.assertEqual(raw.getvalue(), b"CHANGED: a\\udcffb\xc3\xa9\n")

    def main_with(self, check=None, bash="bash"):
        """Run main() with the given check function and bash path. Return the exit code and the text of stderr."""
        raw = io.BytesIO()
        with (mock.patch.object(fc, "check", check),
              mock.patch.object(fc, "find_bash", lambda: bash),
              mock.patch.object(signal, "signal"),
              mock.patch.object(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8")),
              mock.patch.object(sys, "stderr", io.TextIOWrapper(raw, encoding="utf-8", write_through=True))):
            code = fc.main(["--fix-commit", "x", "--command", "y"])
            return code, raw.getvalue().decode("utf-8")

    def test_missing_bash_is_a_setup_error(self):
        code, err = self.main_with(bash=None)
        self.assertEqual(code, 2)
        self.assertIn("error: bash not found", err)

    def test_keyboard_interrupt_gives_exit_code_2(self):
        code, err = self.main_with(check=mock.Mock(side_effect=KeyboardInterrupt))
        self.assertEqual(code, 2)
        self.assertIn("error: stopped by a signal", err)

    def test_bash_that_cannot_start_gives_a_start_error(self):
        with tempfile.TemporaryDirectory() as folder:
            job = fc.Run("fix", "a" * 40, Path(folder), "main worktree")
            fc.run_command(job, str(Path(folder) / "no-such-bash"), "true", 5, Path(folder) / "fix.log")
        self.assertIsNotNone(job.start_error)
        self.assertIsNone(job.code)
        self.assertFalse(job.runnable_failure)

    @unittest.skipUnless(os.name == "nt", "the job object is only on Windows")
    def test_shell_that_cannot_join_a_job_gets_no_job(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], stdin=subprocess.DEVNULL)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        with mock.patch.object(fc.KERNEL32, "AssignProcessToJobObject", return_value=0):
            self.assertIsNone(fc.join_job(proc))

    @unittest.skipUnless(os.name == "nt", "the job object is only on Windows")
    def test_shell_that_cannot_join_a_job_is_stopped_by_taskkill(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(remove_tree, folder)
        fix_run = fc.Run("fix", "0" * 40, folder, "main worktree")
        with (mock.patch.object(fc.KERNEL32, "AssignProcessToJobObject", return_value=0),
              mock.patch.object(fc.subprocess, "run", side_effect=subprocess.run) as runs):
            fc.run_command(fix_run, fc.find_bash(), "sleep 30", 1, folder / "fix.log")
        self.assertTrue(fix_run.timed_out)
        self.assertTrue(any(call.args[0][0] == "taskkill" for call in runs.call_args_list), runs.call_args_list)
        self.assertLess(fix_run.seconds, 15, "the stop did not end the shell")

    @unittest.skipUnless(os.name == "nt", "the job object is only on Windows")
    def test_stop_of_a_job_runs_taskkill_then_ends_the_job_then_waits(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], stdin=subprocess.DEVNULL)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        job = fc.join_job(proc)
        self.assertIsNotNone(job)
        self.addCleanup(fc.KERNEL32.CloseHandle, job)
        calls = mock.Mock()
        calls.attach_mock(mock.Mock(wraps=subprocess.run), "run")
        calls.attach_mock(mock.Mock(wraps=fc.KERNEL32.TerminateJobObject), "terminate")
        calls.attach_mock(mock.Mock(wraps=fc.KERNEL32.WaitForSingleObject), "wait")
        with (mock.patch.object(fc.subprocess, "run", calls.run),
              mock.patch.object(fc.KERNEL32, "TerminateJobObject", calls.terminate),
              mock.patch.object(fc.KERNEL32, "WaitForSingleObject", calls.wait)):
            fc.kill_tree(proc, job)
        names = [call[0] for call in calls.mock_calls]
        self.assertEqual(names[:3], ["run", "terminate", "wait"], names)
        self.assertEqual(calls.run.call_args.args[0], ["taskkill", "/F", "/T", "/PID", str(proc.pid)])
        self.assertGreater(calls.wait.call_args_list[0].args[1], 1000, "the first wait has less than 1 s")
        self.assertEqual(proc.returncode, 1)

    @unittest.skipUnless(os.name == "nt", "the job object is only on Windows")
    def test_stop_of_a_job_ends_the_job_when_taskkill_is_interrupted(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], stdin=subprocess.DEVNULL)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        job = fc.join_job(proc)
        self.assertIsNotNone(job)
        self.addCleanup(fc.KERNEL32.CloseHandle, job)
        with (mock.patch.object(fc.subprocess, "run", side_effect=KeyboardInterrupt),
              self.assertRaises(KeyboardInterrupt)):
            fc.kill_tree(proc, job)
        self.assertEqual(proc.wait(timeout=5), 1)

    @unittest.skipUnless(os.name == "nt", "the job object is only on Windows")
    def test_stop_of_a_job_waits_for_each_process_up_to_one_limit(self):
        child = [sys.executable, "-c", "import time; time.sleep(60)"]
        parent = f"import subprocess, time; time.sleep(1); subprocess.Popen({child!r}); time.sleep(60)"
        proc = subprocess.Popen([sys.executable, "-c", parent], stdin=subprocess.DEVNULL)
        job = fc.join_job(proc)
        self.assertIsNotNone(job)
        self.addCleanup(fc.KERNEL32.CloseHandle, job)
        self.addCleanup(proc.wait)
        self.addCleanup(fc.KERNEL32.TerminateJobObject, job, 1)
        members = {}
        deadline = time.monotonic() + 20
        while len(members) < 2 and time.monotonic() < deadline:
            time.sleep(0.1)
            fc.open_job_processes(job, members)
        for handle in members.values():
            fc.KERNEL32.CloseHandle(handle)
        self.assertEqual(len(members), 2, "the job does not hold the shell and its child")
        late = subprocess.Popen(child, stdin=subprocess.DEVNULL)
        self.addCleanup(late.wait)
        self.addCleanup(late.kill)

        def join_late(*args, **options):
            handle = fc.KERNEL32.OpenProcess(fc.PROCESS_TERMINATE | fc.PROCESS_SET_QUOTA, False, late.pid)
            fc.KERNEL32.AssignProcessToJobObject(job, handle)
            fc.KERNEL32.CloseHandle(handle)

        wait = mock.Mock(wraps=fc.KERNEL32.WaitForSingleObject)
        # The third process joins the job during the taskkill step.
        # No call ends a process, so each real wait runs to the limit.
        with (mock.patch.object(fc.KERNEL32, "WaitForSingleObject", wait),
              mock.patch.object(fc.KERNEL32, "TerminateJobObject", return_value=1),
              mock.patch.object(fc.subprocess, "run", side_effect=join_late),
              mock.patch.object(fc, "JOB_WAIT_SECONDS", 1)):
            start = time.monotonic()
            fc.stop_job(job, proc.pid)
            seconds = time.monotonic() - start
        self.assertEqual(wait.call_count, 3, "the stop did not wait for each process of the job")
        self.assertGreater(seconds, 0.9)
        self.assertLess(seconds, 1.7)

    def test_worktree_and_folder_that_stay_give_warn_lines(self):
        top = Path(tempfile.mkdtemp())
        self.addCleanup(remove_tree, top)
        trees = fc.Worktrees(top)
        self.addCleanup(remove_tree, trees.root)
        stuck = trees.root / "fix"
        stuck.mkdir()
        trees.made.append(stuck)
        out = io.StringIO()
        with (mock.patch.object(fc, "git_result", return_value=(1, "", "it is locked")),
              mock.patch.object(shutil, "rmtree"),
              contextlib.redirect_stdout(out)):
            trees.remove()
        self.assertEqual(out.getvalue().splitlines(), [f"WARN: could not delete the folder {trees.root}",
                                                       f"WARN: could not remove the worktree {stuck}: it is locked"])

    def test_export_that_stays_has_no_removed_line(self):
        top = Path(tempfile.mkdtemp())
        self.addCleanup(remove_tree, top)
        trees = fc.Worktrees(top)
        self.addCleanup(remove_tree, trees.root)
        stuck = trees.root / "parent"
        stuck.mkdir()
        trees.exported.append(stuck)
        out = io.StringIO()
        with mock.patch.object(shutil, "rmtree"), contextlib.redirect_stdout(out):
            trees.remove()
        self.assertEqual(out.getvalue().splitlines(), [f"WARN: could not delete the folder {trees.root}"])
        self.assertEqual(trees.exported, [])

    def test_export_that_cannot_make_its_folder_gives_the_error(self):
        top = Path(tempfile.mkdtemp())
        self.addCleanup(remove_tree, top)
        trees = fc.Worktrees(top)
        self.addCleanup(remove_tree, trees.root)
        out = io.StringIO()
        with (mock.patch.object(Path, "mkdir", side_effect=PermissionError("access is denied")),
              contextlib.redirect_stdout(out)):
            self.assertEqual(trees.export("fix", "0" * 40), (None, "access is denied"))
        self.assertEqual((out.getvalue(), trees.exported), ("", []))

    def test_default_time_limit_is_the_one_in_the_skill_text(self):
        self.assertIn(f"after {fc.DEFAULT_TIMEOUT} seconds", SKILL.read_bytes().decode("utf-8"))

    def test_help_text_names_each_kind_of_output_line(self):
        for kind in ("FIX <sha>", "MAIN WORKTREE:", "CHANGED:", "MADE <path>", "NO WORKTREE:", "EXPORTED <path>", "RUN <side>",
                     "ERROR |", "TAIL  |", "REMOVED <path>", "WARN:", "VERDICT:", "REASON:"):
            self.assertIn(kind, fc.__doc__)

    def test_forms_of_a_windows_folder(self):
        self.assertEqual(fc.path_forms(PureWindowsPath("C:\\work\\my repo")),
                         {"C:\\work\\my repo", "C:/work/my repo", "C:/work/my%20repo", "/c/work/my repo"})

    def test_bash_on_windows_is_the_one_next_to_git(self):
        if os.name != "nt":
            return
        with tempfile.TemporaryDirectory() as folder:
            core = Path(folder) / "Git" / "mingw64" / "libexec" / "git-core"
            bash = Path(folder) / "Git" / "usr" / "bin" / "bash.exe"
            core.mkdir(parents=True)
            bash.parent.mkdir(parents=True)
            bash.touch()
            with mock.patch.object(fc, "git", return_value=f"{core}\n"):
                self.assertEqual(fc.find_bash(), str(bash))

    def test_bash_is_not_a_wsl_launcher(self):
        bash = fc.find_bash()
        if os.name == "nt":
            self.assertNotIn("\\windows\\", bash.lower())
            self.assertNotIn("windowsapps", bash.lower())
        else:
            self.assertEqual(bash, shutil.which("bash"))


class TestCountTests(unittest.TestCase):
    """The count lines of unittest, pytest, and dotnet test, as each runner prints them (issue #230)."""

    def signatures(self, fix_lines, parent_lines):
        fix = fc.Run("fix", "a" * 40, "x", "main")
        fix.lines = fix_lines
        parent = fc.Run("parent", "b" * 40, "y", "temp")
        parent.lines = parent_lines
        return fix.signature(set()), parent.signature(set())

    def assertSame(self, fix_lines, parent_lines):
        fix, parent = self.signatures(fix_lines, parent_lines)
        self.assertEqual(fix, parent)

    def assertDiffer(self, fix_lines, parent_lines):
        fix, parent = self.signatures(fix_lines, parent_lines)
        self.assertNotEqual(fix, parent)

    def test_count_line_of_unittest_does_not_count(self):
        failure = ["FAIL: test_add (test_calc.CalcTests.test_add)", "AssertionError: 2 != 3"]
        self.assertSame([*failure, "Ran 3 tests in 0.001s", "FAILED (failures=1)"],
                        [*failure, "Ran 2 tests in 0.001s", "FAILED (failures=1)"])
        self.assertSame([*failure, "Ran 2 tests in 0.001s"], [*failure, "Ran 1 test in 0.000s"])
        self.assertSame([*failure, "Ran 120 tests in 0.5s"], [*failure, "Ran 119 tests in 0.5s"])
        self.assertSame([*failure, "FAILED (failures=1, skipped=2)"], [*failure, "FAILED (failures=1, skipped=1)"])
        self.assertDiffer([*failure, "FAILED (failures=2, skipped=1)"], [*failure, "FAILED (failures=1, skipped=1)"])
        self.assertSame([*failure, "OK (skipped=12)"], [*failure, "OK (skipped=3)"])

    def test_counts_of_pytest_do_not_count(self):
        failure = ["FAILED test_class.py::TestClass::test_two - AssertionError: assert False"]
        self.assertSame([*failure, "1 failed, 2 passed in 0.12s"], [*failure, "1 failed, 1 passed in 0.12s"])
        each_kind = "1 failed, {} passed, {} skipped, {} deselected, {} xfailed, {} xpassed, 1 error in 0.12s"
        self.assertSame([*failure, "= " + each_kind.format(12, 1, 4, 2, 3) + " ="],
                        [*failure, "== " + each_kind.format(1, 3, 2, 1, 1) + " =="])
        self.assertSame([*failure, "============================ 1 failed in 0.12s ============================="],
                        [*failure, "=========================== 1 failed in 10.12s ============================="])
        self.assertSame([*failure, "1 failed, 2 passed, 3 subtests passed in 75.12s (0:01:15)"],
                        [*failure, "1 failed, 1 passed, 2 subtests passed in 75.12s (0:01:15)"])
        self.assertSame([*failure, "3 failed, 45 passed in 0.12s"], [*failure, "3 failed, 44 passed in 0.12s"])

    def test_colored_summary_of_pytest_does_not_count(self):
        failure = ["FAILED test_class.py::TestClass::test_two - AssertionError: assert False"]
        colored = "\x1b[31m\x1b[31m\x1b[1m1 failed\x1b[0m, \x1b[32m{} passed\x1b[0m\x1b[31m in 0.08s\x1b[0m\x1b[0m"
        self.assertSame([*failure, colored.format(2)], [*failure, colored.format(1)])

    def test_progress_of_pytest_does_not_count(self):
        self.assertSame(["test_verbosity_example.py::test_words_fail FAILED                    [ 50%]"],
                        ["test_verbosity_example.py::test_words_fail FAILED                    [100%]"])
        self.assertSame(["test_a.py::test_x FAILED    [  4%]"], ["test_a.py::test_x FAILED    [  5%]"])

    def test_counts_of_dotnet_test_do_not_count(self):
        failure = ["  Failed Add_ReturnsSum [38 ms]"]
        self.assertSame(
            [*failure, "Failed!  - Failed:     1, Passed:     2, Skipped:     0, Total:     3, Duration: 32 ms - "
                       "Calc.Tests.dll (net10.0)"],
            [*failure, "Failed!  - Failed:     1, Passed:     1, Skipped:     0, Total:     2, Duration: 41 ms - "
                       "Calc.Tests.dll (net10.0)"],
        )
        self.assertSame(
            [*failure, "Failed!  - Failed:     1, Passed:    12, Skipped:     0, Total:    13, Duration: 32 ms"],
            [*failure, "Failed!  - Failed:     1, Passed:    11, Skipped:     0, Total:    12, Duration: 41 ms"],
        )

    def test_counts_of_the_testing_platform_do_not_count(self):
        failure = ["failed Add_ReturnsSum (41ms)", "Test run summary: Failed!"]
        self.assertSame([*failure, "  total: 3", "  failed: 1", "  succeeded: 2", "  skipped: 0", "  duration: 635ms"],
                        [*failure, "  total: 2", "  failed: 1", "  succeeded: 1", "  skipped: 0", "  duration: 672ms"])
        self.assertSame([*failure, "  total: 13", "  succeeded: 12", "  skipped: 10"],
                        [*failure, "  total: 12", "  succeeded: 11", "  skipped: 11"])

    def test_count_of_failures_still_counts(self):
        self.assertDiffer(["FAIL: test_add", "FAILED (failures=2)"], ["FAIL: test_add", "FAILED (failures=1)"])
        self.assertDiffer(["2 failed, 1 passed in 0.12s"], ["1 failed, 1 passed in 0.12s"])
        self.assertDiffer(["1 failed, 1 passed, 3 errors in 0.12s"], ["1 failed, 1 passed, 2 errors in 0.12s"])
        self.assertDiffer(["Failed!  - Failed:     2, Passed:     1, Skipped:     0, Total:     3, Duration: 1 s"],
                          ["Failed!  - Failed:     1, Passed:     1, Skipped:     0, Total:     2, Duration: 1 s"])
        self.assertDiffer(["Test run summary: Failed!", "  failed: 2"], ["Test run summary: Failed!", "  failed: 1"])

    def test_number_outside_a_count_line_still_counts(self):
        for fix_line, parent_line in (("AssertionError: 3 passed != 2", "AssertionError: 2 passed != 2"),
                                      ("3 passed in 2s, expected 2", "2 passed in 2s, expected 2"),
                                      ("error: Ran 3 tests, expected 2", "error: Ran 2 tests, expected 2"),
                                      ("total: 3 of 4", "total: 2 of 4"),
                                      ("total: 130", "total: 120"),
                                      ("error: total: 3", "error: total: 2"),
                                      ("error: Passed: 3", "error: Passed: 2"),
                                      ("error at [ 50%] of the file", "error at [ 75%] of the file"),
                                      ("AssertionError: 'FAILED (skipped=3)'", "AssertionError: 'FAILED (skipped=2)'")):
            with self.subTest(line=fix_line):
                self.assertDiffer(["FAIL: test_x", fix_line], ["FAIL: test_x", parent_line])


class SignalTests(FailureCheckCase):
    """The command is a bash loop. It ends at the stop file or after its last step, and then writes the flag file."""

    START_SECONDS = 30
    REPLY_SECONDS = 2

    def end(self, proc):
        if proc.poll() is None:
            proc.kill()
            proc.communicate()

    def stop_with(self, name, marker="MADE "):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        started, stop, flag = (self.tmp / f"{name}-{part}" for part in ("started", "stop", "flag"))
        self.addCleanup(stop.touch)
        command = (": > {}; for i in $(seq 600); do [ -e {} ] && break; sleep 0.1; done; echo alive > {}"
                   .format(*(shlex.quote(path.as_posix()) for path in (started, stop, flag))))
        windows = os.name == "nt"
        proc = subprocess.Popen([sys.executable, "-I", str(SCRIPT), "--fix-commit", fix, "--command", command,
                                 "--cwd", str(self.repo / "sub")], env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0)
        self.addCleanup(self.end, proc)
        line = proc.stdout.readline()
        while line and not line.startswith(marker):
            line = proc.stdout.readline()
        self.assertTrue(line.startswith(marker))
        deadline = time.monotonic() + self.START_SECONDS
        while not started.exists():
            self.assertLess(time.monotonic(), deadline, "the command did not start")
            time.sleep(0.1)
        proc.send_signal(getattr(signal, name))
        out, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 2, err)
        self.assertIn("REMOVED ", out)
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertFalse(Path(line[len(marker):].strip()).exists())
        stop.touch()
        deadline = time.monotonic() + self.REPLY_SECONDS
        while not flag.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(flag.exists(), "the command ran on after the signal")

    def test_stop_signal_stops_the_command_and_removes_the_worktrees(self):
        names = ["CTRL_BREAK_EVENT"] if os.name == "nt" else ["SIGTERM", "SIGHUP"]
        for name in names:
            with self.subTest(signal=name):
                self.stop_with(name)
                self.git("clean", "-fdq")
                self.git("reset", "-q", "--hard", self.base)

    def test_stop_signal_stops_the_command_and_removes_the_export(self):
        block_worktrees(self.repo)
        self.stop_with("CTRL_BREAK_EVENT" if os.name == "nt" else "SIGTERM", marker="EXPORTED ")


class TreeKillTests(FailureCheckCase):
    """The child is a bash loop. It ends at the stop file or after its last step, and then writes the flag file."""

    CHILD_STEPS = 600
    REPLY_SECONDS = 3

    def test_time_limit_stops_a_background_child_of_the_command(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        stop, flag = self.tmp / "stop", self.tmp / "flag.txt"
        quoted = shlex.quote(stop.as_posix())
        loop = (f"for i in $(seq {self.CHILD_STEPS}); do [ -e {quoted} ] && break; sleep 0.1; done; "
                f"echo alive > {shlex.quote(flag.as_posix())}")
        self.addCleanup(stop.touch)
        args = [sys.executable, "-I", SCRIPT, "--fix-commit", fix, "--command",
                f'("$BASH" -c {shlex.quote(loop)}; true) & wait', "--cwd", self.repo / "sub", "--timeout", "1"]
        result = run(args, env=self.env, timeout=120)
        self.assertResult(result, 0, "stopped after the time limit of 1 s", "VERDICT: OTHER")
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1, "a worktree is left")
        self.assertEqual(list(self.temp.iterdir()), [], "a temporary folder is left")
        self.assertNotIn("WARN", result.stdout)
        stop.touch()
        deadline = time.monotonic() + self.REPLY_SECONDS
        while not flag.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(flag.exists(), "the child of the command ran on after the time limit")


if __name__ == "__main__":
    unittest.main()
