"""Tests for essentials/dev-essentials/skills/review-loop/scripts/failure_check.py.

Each test builds a git repository in a temporary folder with a base commit and
a fix commit, and runs the script as a child process, as Phase 6 of review-loop
does. The commands are short bash lines, so no test builds a project.
"""
import io
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

from support import REPO, load_module, tool_missing
from testkit import ScratchCase, clean_env, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/skills/review-loop/scripts/failure_check.py"
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
        self.assertIn("RUN fix", out)
        self.assertIn("ERROR | error: value.txt is bad", out)
        self.assertIn("TAIL  | error: value.txt is bad", out)
        self.assertRegex(out, r"RUN parent \w+ in temporary worktree .*review-loop-fc-\S+[/\\]parent[/\\]sub: exit 0")

    def test_failure_of_uncommitted_changes_points_to_the_main_worktree(self):
        self.write("sub/other.txt", "fix\n")
        fix = self.commit("fix")
        self.write("sub/value.txt", "broken by hand\n")
        out = self.check(fix)
        self.assertEqual(self.verdict(out), "UNCOMMITTED")
        self.assertIn("CHANGED: sub/value.txt", out)
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


class IgnoreAndLimitTests(FailureCheckCase):
    def test_ignored_files_of_the_loop_do_not_count(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("Notes/Reviews/branch-cycle-1.md", "report\n")
        out = self.check(fix, CHECK, "--ignore", "Notes/Reviews/branch-*")
        self.assertIn("MAIN WORKTREE: clean", out)
        self.assertNotIn("CHANGED:", out)

    def test_time_limit_stops_the_command(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        start = time.monotonic()
        out = self.check(fix, "sleep 60", "--timeout", "2")
        self.assertLess(time.monotonic() - start, 45)
        self.assertIn("stopped after the time limit of 2 s", out)
        self.assertEqual(self.verdict(out), "OTHER")

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
        (hooks / "post-checkout").write_bytes(b"#!/bin/sh\nexit 1\n")
        os.chmod(hooks / "post-checkout", 0o755)
        self.git("config", "core.hooksPath", hooks.as_posix())
        out = self.check(fix)
        self.assertIn("git worktree add failed", out)
        self.assertEqual(self.verdict(out), "OTHER")

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

    def test_folder_outside_the_work_tree_is_refused(self):
        result = run([sys.executable, "-I", SCRIPT, "--fix-commit", "HEAD", "--command", "true",
                      "--cwd", self.temp], env=self.env)
        self.assertEqual(result.returncode, 2)


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
        with (mock.patch.object(fc, "check", lambda args, bash: print("CHANGED: a\udcffb")),
              mock.patch.object(fc, "find_bash", lambda: "bash"),
              mock.patch.object(signal, "signal"),
              mock.patch.object(sys, "stdout", out)):
            code = fc.main(["--fix-commit", "x", "--command", "y"])
        out.flush()
        self.assertEqual(code, 0)
        self.assertEqual(raw.getvalue(), b"CHANGED: a\\udcffb\n")

    def test_bash_is_not_a_wsl_launcher(self):
        bash = fc.find_bash()
        if os.name == "nt":
            self.assertNotIn("\\windows\\", bash.lower())
            self.assertNotIn("windowsapps", bash.lower())
        else:
            self.assertEqual(bash, shutil.which("bash"))


class SignalTests(FailureCheckCase):
    def stop_with(self, number):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        self.write("sub/dirty.txt", "x\n")
        windows = os.name == "nt"
        proc = subprocess.Popen([sys.executable, "-I", str(SCRIPT), "--fix-commit", fix, "--command", "sleep 60",
                                 "--cwd", str(self.repo / "sub")], env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0)
        line = proc.stdout.readline()
        while line and not line.startswith("MADE "):
            line = proc.stdout.readline()
        self.assertTrue(line.startswith("MADE "))
        time.sleep(1)
        proc.send_signal(number)
        out, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 2, err)
        self.assertIn("REMOVED ", out)
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertFalse(Path(line[len("MADE "):].strip()).exists())

    def test_stop_signal_removes_the_worktrees(self):
        names = ["CTRL_BREAK_EVENT"] if os.name == "nt" else ["SIGTERM", "SIGHUP"]
        for name in names:
            with self.subTest(signal=name):
                self.stop_with(getattr(signal, name))
                self.git("clean", "-fdq")
                self.git("reset", "-q", "--hard", self.base)


class TreeKillTests(FailureCheckCase):
    """On Windows, taskkill does not reach every child of the shell, so only Linux checks the child."""

    def test_time_limit_stops_a_background_child_of_the_command(self):
        self.write("sub/value.txt", "bad\n")
        fix = self.commit("fix")
        flag = self.tmp / "flag.txt"
        command = f"(sleep 4; echo alive > {shlex.quote(flag.as_posix())}) & wait"
        self.check(fix, command, "--timeout", "1")
        if os.name == "nt":
            return
        deadline = time.monotonic() + 8
        while not flag.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        self.assertFalse(flag.exists(), "the child of the command ran on after the time limit")


if __name__ == "__main__":
    unittest.main()
