"""Tests for essentials/dev-essentials/skills/implement-batch/scripts/squash_task.py.

Each test builds a git repository in a temporary folder: a base commit and the commits of a task. Most tests
run the script as a child process, as the implement-batch skill does. An empty global git configuration and
no system configuration keep the settings of the machine (hooks, signing) out of the commits.
"""
import contextlib
import io
import os
import shutil
import stat
import subprocess
import sys
from unittest import mock

from support import REPO, load_module, tool_missing
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/skills/implement-batch/scripts/squash_task.py"
sq = load_module("squash_task", SCRIPT)
MESSAGE = "Task 1 — add the option (implement + 2 review rounds)\n\nThe body names the change."


class SquashCase(ScratchCase):
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
        self.base = self.commit("base", "a.txt")

    def git(self, *args, cwd=None):
        return run(["git", "-C", cwd or self.repo, *args], check=True).stdout.strip()

    def write(self, rel, text, cwd=None):
        path = (cwd or self.repo) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit(self, subject, rel, text=None, cwd=None):
        """Write a file, commit it with the subject, and return the full SHA."""
        self.write(rel, subject + "\n" if text is None else text, cwd)
        self.git("add", "--", rel, cwd=cwd)
        self.git("commit", "-q", "-m", subject, cwd=cwd)
        return self.git("rev-parse", "HEAD", cwd=cwd)

    def task(self, count=3, cwd=None):
        return [self.commit(f"task step {n}", f"src/step{n}.txt", cwd=cwd) for n in range(1, count + 1)]

    def squash(self, *commits, base=None, code=0, message=MESSAGE, extra=(), repo=None):
        args = [sys.executable, "-I", SCRIPT, "--repo", repo or self.repo, "--base", base or self.base,
                "--message", message]
        for sha in commits:
            args += ["--commit", sha]
        result = run([*args, *extra])
        self.assertResult(result, code)
        return result.stdout

    def head(self, cwd=None):
        return self.git("rev-parse", "HEAD", cwd=cwd)

    def hook(self, name, body):
        """Write a commit hook into a folder outside the work tree, and point core.hooksPath at it."""
        folder = self.tmp / "hooks"
        folder.mkdir(exist_ok=True)
        path = folder / name
        path.write_bytes(("#!/bin/sh\n" + body).encode("utf-8"))
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        self.git("config", "core.hooksPath", folder.as_posix())

    def in_process(self, *argv):
        """Run execute() in this process. Return the exit code and stdout."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = sq.execute(sq.parse_args([str(part) for part in argv]))
        return code, out.getvalue()


class PlanTests(SquashCase):
    def test_plan_lists_the_task_commits_and_changes_nothing(self):
        commits = self.task()
        out = self.squash(*commits)
        self.assertIn("MODE PLAN: nothing changes", out)
        for sha in commits:
            self.assertIn(f"COMMIT {sha[:12]} TASK task step", out)
        self.assertIn(f"BASE {self.base[:12]} base", out)
        self.assertIn("MESSAGE Task 1 — add the option", out)
        self.assertIn("RESULT: READY. 3 commits squash into one commit", out)
        self.assertEqual(self.head(), commits[-1])

    def test_short_shas_work(self):
        commits = self.task(2)
        out = self.squash(*[sha[:7] for sha in commits], base=self.base[:7])
        self.assertIn("RESULT: READY. 2 commits", out)

    def test_one_commit_is_left_as_it_is(self):
        (sha,) = self.task(1)
        out = self.squash(sha, extra=["--apply"])
        self.assertIn(f"RESULT: ONE COMMIT. {sha[:12]}", out)
        self.assertNotIn("OLD HEAD", out)
        self.assertEqual(self.head(), sha)
        self.assertEqual(self.git("log", "-1", "--format=%s"), "task step 1")

    def test_untracked_file_is_listed_and_does_not_block(self):
        commits = self.task(2)
        self.write("notes.txt", "draft\n")
        out = self.squash(*commits)
        self.assertIn("UNTRACKED notes.txt", out)
        self.assertIn("RESULT: READY", out)

    def test_untracked_folder_is_one_line_with_each_status_setting(self):
        commits = self.task(2)
        self.git("config", "status.showUntrackedFiles", "no")
        self.write("drafts/one.txt", "1\n")
        self.write("drafts/two.txt", "2\n")
        out = self.squash(*commits)
        self.assertIn("UNTRACKED drafts/", out)
        self.assertEqual(out.count("UNTRACKED "), 1)

    def test_repository_path_with_a_space_and_non_ascii_letters(self):
        self.repo = git_init(self.tmp / "my répo")
        self.base = self.commit("base", "a.txt")
        commits = self.task(2)
        out = self.squash(*commits, extra=["--apply"])
        self.assertIn("my répo", out)
        self.assertIn("RESULT: SQUASHED", out)

    def test_output_is_short_for_an_agent(self):
        commits = [self.commit("x" * 300, "long.txt"), self.commit("tab\there", "tab.txt"), *self.task(3)]
        for name in ("u1", "u2", "u3"):
            self.write(f"{name}.txt", "draft\n")
        with mock.patch.object(sq, "MAX_COMMITS", 3), mock.patch.object(sq, "MAX_PATHS", 2):
            code, out = self.in_process("--repo", self.repo, "--base", self.base, "--message", "m",
                                        *[part for sha in commits for part in ("--commit", sha)])
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count(" TASK "), 3)
        self.assertIn("COMMIT ... 2 more commits", out)
        self.assertIn("more characters", out)
        self.assertIn('TASK "tab\\there"', out)
        self.assertEqual(out.count("UNTRACKED u"), 2)
        self.assertIn("UNTRACKED ... 1 more", out)
        self.assertTrue(all(len(line) <= sq.LINE_CHARS + 40 for line in out.splitlines()))


class ApplyTests(SquashCase):
    def test_apply_makes_one_commit_on_the_base_with_the_message(self):
        commits = self.task()
        branch = self.git("symbolic-ref", "HEAD")
        old_tree = self.git("rev-parse", "HEAD^{tree}")
        self.write("notes.txt", "draft\n")
        out = self.squash(*commits, extra=["--apply"])
        new = self.head()
        self.assertIn(f"OLD HEAD {commits[-1]}", out)
        self.assertIn(f"NEW {new}", out)
        self.assertIn(f"PARENT {self.base[:12]}", out)
        self.assertIn("TREE same as the old HEAD", out)
        self.assertIn(f"To undo, run: git reset --soft {commits[-1]}", out)
        self.assertNotIn("WARN", out)
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")
        self.assertEqual(self.git("rev-parse", "HEAD^"), self.base)
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}"), old_tree)
        self.assertEqual(self.git("log", "-1", "--format=%B"), MESSAGE)
        self.assertEqual(self.git("symbolic-ref", "HEAD"), branch)
        self.assertEqual(self.git("status", "--porcelain"), "?? notes.txt")

    def test_apply_in_a_linked_worktree_moves_only_its_branch(self):
        main_head = self.head()
        tree = self.tmp / "wt"
        self.git("worktree", "add", "-q", "-b", "task", str(tree))
        commits = self.task(cwd=tree)
        out = self.squash(*commits, extra=["--apply"], repo=tree / "src")
        self.assertIn("on refs/heads/task", out)
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD", cwd=tree), "1")
        self.assertEqual(self.head(), main_head)

    def test_commit_hooks_run(self):
        commits = self.task(2)
        self.hook("commit-msg", 'printf "hooked\\n" >> "$1"\n')
        self.squash(*commits, extra=["--apply"])
        self.assertEqual(self.git("log", "-1", "--format=%B"), MESSAGE + "\nhooked")

    def test_failed_commit_puts_the_old_head_back(self):
        commits = self.task()
        self.hook("pre-commit", 'echo "lint: line 3 is too long" >&2\nexit 1\n')
        out = self.squash(*commits, extra=["--apply"], code=1)
        self.assertIn("FAILED git commit: exit code 1", out)
        self.assertIn("OUTPUT | lint: line 3 is too long", out)
        self.assertIn(f"RESTORED HEAD {commits[-1][:12]}", out)
        self.assertIn("RESULT: FAILED. No squash", out)
        self.assertEqual(self.head(), commits[-1])
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_output_of_a_failed_commit_is_short(self):
        commits = self.task(2)
        self.hook("pre-commit", 'i=0\nwhile [ $i -lt 30 ]; do\n  echo "lint $i ' + "x" * 300 + '"\n  i=$((i+1))\ndone\n'
                                'exit 1\n')
        out = self.squash(*commits, extra=["--apply"], code=1)
        lines = [line for line in out.splitlines() if line.startswith("OUTPUT | ")]
        self.assertEqual(len(lines), sq.MAX_PATHS)
        self.assertTrue(lines[-1].startswith("OUTPUT | lint 29 x"), lines[-1])
        self.assertTrue(all("more characters" in line and len(line) <= sq.LINE_CHARS + 40 for line in lines), lines)
        self.assertEqual(self.head(), commits[-1])

    def test_old_head_line_comes_before_the_commit_ends(self):
        commits = self.task(2)
        go = self.tmp / "go"
        self.hook("pre-commit", f'n=0\nwhile [ ! -f "{go.as_posix()}" ]; do\n  n=$((n+1))\n'
                                '  if [ $n -gt 100 ]; then exit 1; fi\n  sleep 0.1\ndone\n')
        args = [sys.executable, "-I", str(SCRIPT), "--repo", str(self.repo), "--base", self.base, "--message", "m",
                "--apply"]
        for sha in commits:
            args += ["--commit", sha]
        lines = []
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
            for raw in proc.stdout:
                lines.append(raw.decode("utf-8").rstrip())
                if lines[-1].startswith("OLD HEAD "):
                    go.write_bytes(b"")
        self.assertIn(f"OLD HEAD {commits[-1]}", lines)
        self.assertEqual(lines[-1][:16], "RESULT: SQUASHED", lines)

    def test_stop_during_the_commit_puts_the_old_head_back(self):
        commits = self.task(2)
        real = sq.git_result

        def stopped(repo, *args, data=None):
            if args[0] == "commit":
                raise KeyboardInterrupt
            return real(repo, *args, data=data)

        out = io.StringIO()
        with mock.patch.object(sq, "git_result", side_effect=stopped), contextlib.redirect_stdout(out), \
                self.assertRaises(KeyboardInterrupt):
            sq.execute(sq.parse_args(["--repo", str(self.repo), "--base", self.base, "--message", "m", "--apply",
                                      "--commit", commits[0], "--commit", commits[1]]))
        self.assertIn(f"OLD HEAD {commits[-1]}", out.getvalue())
        self.assertIn(f"RESTORED HEAD {commits[-1][:12]}", out.getvalue())
        self.assertEqual(self.head(), commits[-1])
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_message_that_is_not_unicode_changes_nothing(self):
        commits = self.task(2)
        message = "bad " + chr(0xD800)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(UnicodeEncodeError):
            sq.execute(sq.parse_args(["--repo", str(self.repo), "--base", self.base, "--message", message,
                                      "--apply", "--commit", commits[0], "--commit", commits[1]]))
        self.assertEqual(self.head(), commits[-1])

    def test_result_line_keeps_the_undo_command_on_a_long_branch_name(self):
        self.git("checkout", "-q", "-b", "tasks/" + "n" * 120)
        commits = self.task(2)
        out = self.squash(*commits, extra=["--apply"])
        self.assertTrue(out.splitlines()[-1].endswith(f"To undo, run: git reset --soft {commits[-1]}"), out)

    def test_hook_that_changes_the_tree_gives_a_warning(self):
        commits = self.task(2)
        self.hook("pre-commit", 'echo hooked >> a.txt\ngit add a.txt\n')
        out = self.squash(*commits, extra=["--apply"])
        self.assertIn("TREE differs from the old HEAD", out)
        self.assertIn("WARN: a commit hook changed the commit", out)
        self.assertIn("RESULT: SQUASHED", out)

    def test_failed_restore_names_the_command_that_restores(self):
        commits = self.task(2)
        real = sq.git_result

        def failing(repo, *args, data=None):
            if args[0] == "commit" or (args[0] == "update-ref" and args[2] == "squash_task: restore"):
                return 1, "", "simulated failure"
            return real(repo, *args, data=data)

        with mock.patch.object(sq, "git_result", side_effect=failing):
            code, out = self.in_process("--repo", self.repo, "--base", self.base, "--message", "m", "--apply",
                                        *[part for sha in commits for part in ("--commit", sha)])
        self.assertEqual(code, 1, out)
        self.assertIn(f"RESULT: FAILED, NOT RESTORED. HEAD is at the base {self.base[:12]}", out)
        self.assertIn(f"run: git reset --soft {commits[-1]}", out)
        self.assertEqual(self.head(), self.base)

    def test_head_that_moved_after_the_check_stays(self):
        commits = self.task(2)
        args = sq.parse_args(["--repo", str(self.repo), "--base", self.base, "--message", "m", "--apply",
                              *[part for sha in commits for part in ("--commit", sha)]])
        state = sq.inspect(args)
        late = self.commit("late commit", "late.txt")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = sq.apply(state, args.message)
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("RESULT: FAILED. Nothing changed.", out.getvalue())
        self.assertEqual(self.head(), late)


class RefusalTests(SquashCase):
    def refused(self, *commits, reason, base=None, extra=(), repo=None):
        before = self.git("rev-parse", "HEAD")
        status = self.git("status", "--porcelain")
        out = self.squash(*commits, base=base, code=3, extra=["--apply", *extra], repo=repo)
        self.assertIn("RESULT: REFUSED. Nothing changed.", out)
        self.assertIn(f"REFUSED: {reason}", out)
        self.assertNotIn("OLD HEAD", out)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(self.git("status", "--porcelain"), status)
        return out

    def test_commit_of_someone_else_in_the_range(self):
        first = self.commit("task step 1", "a1.txt")
        other = self.commit("a commit of the user", "user.txt")
        last = self.commit("task step 2", "a2.txt")
        out = self.refused(first, last, reason="commits of the range that are not a --commit: 1.")
        self.assertIn(f"COMMIT {other[:12]} OTHER a commit of the user", out)

    def test_commit_that_is_not_in_the_range(self):
        commits = self.task(2)
        self.refused(*commits, self.base, reason=f"--commit {self.base} is not a commit of the range")

    def test_unknown_commit(self):
        commits = self.task(2)
        out = self.refused(*commits, "0123456789abc", reason="--commit 0123456789abc names no single commit")
        self.assertIn("MISSING 0123456789abc: names no single commit", out)

    def test_unknown_base(self):
        commits = self.task(2)
        out = self.refused(*commits, base="0123456789abc", reason="the base names no single commit.")
        self.assertIn("BASE 0123456789abc: names no single commit", out)

    def test_branch_name_that_looks_like_a_sha(self):
        commits = self.task(2)
        self.git("branch", "abcdef12", self.base)
        self.refused(*commits, "abcdef12", reason="--commit abcdef12 names no single commit")

    def test_base_that_is_not_an_ancestor(self):
        branch = self.git("symbolic-ref", "--short", "HEAD")
        self.git("checkout", "-q", "-b", "side")
        side = self.commit("side", "side.txt")
        self.git("checkout", "-q", branch)
        commits = self.task(2)
        self.refused(*commits, base=side, reason="the base is not an ancestor of HEAD")

    def test_empty_range(self):
        self.refused(self.base, reason="the range is empty: HEAD is the base")

    def test_merge_commit_in_the_range(self):
        branch = self.git("symbolic-ref", "--short", "HEAD")
        first = self.commit("task step 1", "a1.txt")
        self.git("checkout", "-q", "-b", "side", self.base)
        side = self.commit("side", "side.txt")
        self.git("checkout", "-q", branch)
        self.git("merge", "-q", "--no-ff", "--no-edit", "side")
        out = self.refused(first, side, self.head(), reason="merge commits in the range: 1.")
        self.assertIn(f"COMMIT {self.head()[:12]} MERGE", out)

    def test_staged_change(self):
        commits = self.task(2)
        self.write("a.txt", "staged\n")
        self.git("add", "a.txt")
        out = self.refused(*commits, reason="tracked files with a change: 1.")
        self.assertIn("CHANGED M  a.txt", out)

    def test_unstaged_change(self):
        commits = self.task(2)
        self.write("a.txt", "not staged\n")
        out = self.refused(*commits, reason="tracked files with a change: 1.")
        self.assertIn("CHANGED  M a.txt", out)
        self.assertEqual((self.repo / "a.txt").read_bytes(), b"not staged\n")

    def test_staged_rename_is_an_added_and_a_deleted_file(self):
        commits = self.task(2)
        self.git("mv", "a.txt", "b.txt")
        out = self.refused(*commits, reason="tracked files with a change: 2.")
        self.assertIn("CHANGED A  b.txt", out)
        self.assertIn("CHANGED D  a.txt", out)

    def test_detached_head(self):
        commits = self.task(2)
        self.git("checkout", "-q", "--detach")
        self.refused(*commits, reason="HEAD is detached")

    def test_operation_in_progress(self):
        branch = self.git("symbolic-ref", "--short", "HEAD")
        self.git("checkout", "-q", "-b", "side")
        self.commit("side", "side.txt")
        self.git("checkout", "-q", branch)
        commits = self.task(2)
        self.git("merge", "-q", "--no-ff", "--no-commit", "side")
        self.refused(*commits, reason="a git operation is in progress (MERGE_HEAD exists)")

    def test_each_kind_of_operation_in_progress(self):
        commits = self.task(2)
        for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "BISECT_LOG"):
            with self.subTest(name):
                marker = self.repo / ".git" / name
                if name.startswith("rebase-"):
                    marker.mkdir()
                else:
                    marker.write_bytes((commits[0] + "\n").encode("ascii"))
                try:
                    self.refused(*commits, reason=f"a git operation is in progress ({name} exists)")
                finally:
                    if marker.is_dir():
                        marker.rmdir()
                    else:
                        marker.unlink()

    def test_no_change_in_sum(self):
        added = self.commit("add a file", "tmp.txt")
        self.git("rm", "-q", "tmp.txt")
        self.git("commit", "-q", "-m", "remove the file")
        self.refused(added, self.head(), reason="the commits of the range change no file in sum")

    def test_plan_file_in_the_range(self):
        first = self.commit("task step 1", "a1.txt")
        plan = self.commit("add the plan", "Notes/Plans/task-plan.md")
        out = self.refused(first, plan, reason="files below --plan-dir that the commits of the range change: 1.",
                           extra=["--plan-dir", "Notes/Plans"])
        self.assertIn("PLAN FILE Notes/Plans/task-plan.md", out)

    def test_staged_plan_file(self):
        self.base = self.commit("plan", "Notes/Plans/task-plan.md")
        commits = self.task(2)
        self.write("Notes/Plans/task-plan.md", "- [x] step 1\n")
        self.write("Notes/Plans/new-notes.md", "draft\n")
        self.git("add", "Notes/Plans")
        out = self.refused(*commits, reason="tracked files with a change: 2.", extra=["--plan-dir", "Notes/Plans"])
        self.assertIn("CHANGED A  Notes/Plans/new-notes.md", out)
        self.assertIn("CHANGED M  Notes/Plans/task-plan.md", out)

    def test_plan_file_that_the_task_moved_out_of_the_plan_dir(self):
        self.base = self.commit("plan", "Notes/Plans/task-plan.md", "line 1\nline 2\nline 3\n")
        first = self.commit("task step 1", "a1.txt")
        self.git("mv", "Notes/Plans/task-plan.md", "moved-plan.md")
        self.git("commit", "-q", "-m", "move the plan")
        out = self.refused(first, self.head(), extra=["--plan-dir", "Notes/Plans"],
                           reason="files below --plan-dir that the commits of the range change: 1.")
        self.assertIn("PLAN FILE Notes/Plans/task-plan.md", out)


class PlanDirTests(SquashCase):
    def test_folder_with_the_plan_dir_name_as_a_prefix_is_no_plan_dir(self):
        first = self.commit("task step 1", "a1.txt")
        last = self.commit("task step 2", "Notes/Plans2/real.txt")
        out = self.squash(first, last, extra=["--plan-dir", "Notes/Plans"])
        self.assertNotIn("PLAN FILE", out)
        self.assertIn("RESULT: READY", out)
        self.write("Notes/Plans2/real.txt", "changed\n")
        out = self.squash(first, last, code=3, extra=["--plan-dir", "Notes/Plans"])
        self.assertIn("CHANGED  M Notes/Plans2/real.txt", out)

    def test_untracked_plan_file_gives_no_line(self):
        self.base = self.commit("plan", "Notes/Plans/task-plan.md")
        commits = self.task(2)
        self.write("Notes/Plans/new-notes.md", "draft\n")
        out = self.squash(*commits, extra=["--plan-dir", "Notes/Plans"])
        self.assertNotIn("UNTRACKED", out)
        self.assertIn("RESULT: READY", out)

    def test_changed_plan_file_does_not_block(self):
        self.base = self.commit("plan", "Notes/Plans/task-plan.md")
        commits = self.task(2)
        self.write("Notes/Plans/task-plan.md", "- [x] step 1\n")
        self.squash(*commits, code=3)
        out = self.squash(*commits, extra=["--plan-dir", "Notes/Plans", "--apply"])
        self.assertNotIn("CHANGED", out)
        self.assertIn("RESULT: SQUASHED", out)
        self.assertEqual(self.git("status", "--porcelain"), "M Notes/Plans/task-plan.md")

    def test_absolute_plan_dir_inside_the_work_tree(self):
        first = self.commit("task step 1", "a1.txt")
        plan = self.commit("add the plan", "Notes/Plans/task-plan.md")
        out = self.squash(first, plan, code=3, extra=["--plan-dir", self.repo / "Notes" / "Plans"])
        self.assertIn("PLAN FILE Notes/Plans/task-plan.md", out)

    def test_plan_dir_case_in_a_repository_that_ignores_case(self):
        self.git("config", "core.ignorecase", "true")
        first = self.commit("task step 1", "a1.txt")
        plan = self.commit("add the plan", "Notes/Plans/task-plan.md")
        out = self.squash(first, plan, code=3, extra=["--plan-dir", "notes/plans"])
        self.assertIn("PLAN FILE Notes/Plans/task-plan.md", out)

    def test_plan_dir_outside_the_work_tree(self):
        commits = self.task(2)
        out = self.squash(*commits, extra=["--plan-dir", self.tmp / "notes"])
        self.assertIn("NOTE the plan folder is outside the work tree", out)
        self.assertIn("RESULT: READY", out)

    def test_plan_dir_that_is_the_root_is_a_usage_error(self):
        commits = self.task(2)
        out = self.squash(*commits, code=2, extra=["--plan-dir", "."])
        self.assertEqual(out, "")


class UsageTests(SquashCase):
    def test_usage_errors_change_nothing(self):
        commits = self.task(2)
        head = self.head()
        cases = {
            "no --commit": ["--base", self.base, "--message", "m"],
            "no --message": ["--base", self.base, "--commit", commits[0]],
            "blank message": ["--base", self.base, "--commit", commits[0], "--message", "  \n"],
            "flag as base": ["--base=-x", "--commit", commits[0], "--message", "m"],
            "not hex": ["--base", self.base, "--commit", "zz12345", "--message", "m"],
            "too short": ["--base", self.base[:6], "--commit", commits[0], "--message", "m"],
            "empty plan dir": ["--base", self.base, "--commit", commits[0], "--message", "m", "--plan-dir="],
        }
        for name, args in cases.items():
            with self.subTest(name):
                result = run([sys.executable, "-I", SCRIPT, "--repo", self.repo, "--apply", *args])
                self.assertResult(result, 2, "error:")
                self.assertEqual(result.stdout, "")
                self.assertEqual(self.head(), head)

    def test_folder_that_is_not_a_work_tree(self):
        folder = self.tmp / "plain"
        folder.mkdir()
        result = run([sys.executable, "-I", SCRIPT, "--repo", folder, "--base", self.base, "--commit",
                      self.base, "--message", "m"])
        self.assertResult(result, 2, "error: not inside a git work tree")

    def test_setup_error_shows_the_reason_of_git_before_a_long_path(self):
        folder = self.tmp / ("plain " + "x" * 150)
        folder.mkdir()
        reason = " ".join(run(["git", "-C", folder, "rev-parse", "--show-toplevel"]).stderr.split())
        result = run([sys.executable, "-I", SCRIPT, "--repo", folder, "--base", self.base, "--commit",
                      self.base, "--message", "m"])
        self.assertResult(result, 2, f"error: not inside a git work tree ({reason}): ")

    def test_git_not_found(self):
        commits = self.task(2)
        args = sq.parse_args(["--repo", str(self.repo), "--base", self.base, "--commit", commits[0],
                              "--commit", commits[1], "--message", "m", "--apply"])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sq.shutil, "which", return_value=None), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sq.execute(args)
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, "", "error: git not found\n"))
        self.assertEqual(self.head(), commits[-1])

    def test_help_names_the_exit_codes(self):
        result = run([sys.executable, "-I", SCRIPT, "--help"])
        self.assertResult(result, 0, "Exit codes: 0 = the plan is ready")
