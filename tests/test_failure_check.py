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
        for line in ("AssertionError: " + "A" * 100_000, "error " + "review-loop-fc-" * 14_000):
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

    def test_default_time_limit_is_the_one_in_the_skill_text(self):
        self.assertIn(f"after {fc.DEFAULT_TIMEOUT} seconds", SKILL.read_bytes().decode("utf-8"))

    def test_help_text_names_each_kind_of_output_line(self):
        for kind in ("FIX <sha>", "MAIN WORKTREE:", "CHANGED:", "MADE <path>", "RUN <side>", "ERROR |", "TAIL  |",
                     "REMOVED <path>", "WARN:", "VERDICT:", "REASON:"):
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


class SignalTests(FailureCheckCase):
    """The command is a bash loop. It ends at the stop file or after its last step, and then writes the flag file."""

    START_SECONDS = 30
    REPLY_SECONDS = 2

    def end(self, proc):
        if proc.poll() is None:
            proc.kill()
            proc.communicate()

    def stop_with(self, name):
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
        while line and not line.startswith("MADE "):
            line = proc.stdout.readline()
        self.assertTrue(line.startswith("MADE "))
        deadline = time.monotonic() + self.START_SECONDS
        while not started.exists():
            self.assertLess(time.monotonic(), deadline, "the command did not start")
            time.sleep(0.1)
        proc.send_signal(getattr(signal, name))
        out, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 2, err)
        self.assertIn("REMOVED ", out)
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertFalse(Path(line[len("MADE "):].strip()).exists())
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
