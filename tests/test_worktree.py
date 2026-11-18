"""Tests for essentials/dev-essentials/skills/git-worktree-management/scripts/worktree.py.

Each test builds a git repository with a bare remote origin in a temporary folder. Most tests run the script
as a child process, as the skill git-worktree-management does. An empty global git configuration and no system
configuration keep the settings of the machine out of the repository.
"""
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from support import REPO, load_module, tool_missing
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/skills/git-worktree-management/scripts/worktree.py"
wt = load_module("worktree", SCRIPT)
REF = "feature/tasks/1370383-add-export"
SETTINGS = '{"permissions": {}}\n'


class WorktreeCase(ScratchCase):
    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        super().setUp()
        config = self.tmp / "gitconfig"
        config.write_bytes(b"")
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.repo = self.make_repo(self.tmp / "repo")

    def make_repo(self, path):
        """A repository with one commit on main, a bare remote origin, and origin/HEAD on main."""
        git_init(path)
        self.git("config", "core.autocrlf", "false", cwd=path)
        self.git("checkout", "-q", "-b", "main", cwd=path)
        self.write("README.md", "readme\n", cwd=path)
        self.write(".gitignore", ".claude/worktrees/\n.claude/settings.local.json\nNotes/\n", cwd=path)
        self.git("add", "-A", cwd=path)
        self.git("commit", "-q", "-m", "base", cwd=path)
        origin = path.parent / (path.name + "-origin.git")
        run(["git", "init", "-q", "--bare", origin], check=True)
        self.git("remote", "add", "origin", origin.as_posix(), cwd=path)
        self.git("push", "-q", "origin", "main", cwd=path)
        self.git("remote", "set-head", "origin", "main", cwd=path)
        return path

    def git(self, *args, cwd=None):
        return run(["git", "-C", cwd or self.repo, *args], check=True).stdout.strip()

    def write(self, rel, text, cwd=None):
        path = (cwd or self.repo) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit_all(self, subject, cwd=None):
        self.git("add", "-A", cwd=cwd)
        self.git("commit", "-q", "-m", subject, cwd=cwd)
        return self.git("rev-parse", "HEAD", cwd=cwd)

    def path(self, ref=REF):
        return self.repo.joinpath(".claude", "worktrees", *ref.split("/"))

    def script(self, *args, code=0, cwd=None):
        result = run([sys.executable, "-I", SCRIPT, *args], cwd=cwd or self.repo)
        self.assertResult(result, code)
        return result.stdout

    def is_listed(self, path):
        out = self.git("worktree", "list", "--porcelain")
        listed = [Path(line[len("worktree "):]).resolve() for line in out.splitlines() if line.startswith("worktree ")]
        return path.resolve() in listed

    def branches(self):
        return self.git("for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()

    def has_upstream(self, ref):
        return run(["git", "-C", self.repo, "config", "--get", f"branch.{ref}.merge"]).returncode == 0

    def ends_with(self, out, text):
        self.assertTrue(out.rstrip().endswith(text), out)

    def in_process(self, *argv):
        """Run execute() in this process. Return the exit code and stdout."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = wt.execute(wt.parse_args([str(part) for part in argv]))
        return code, out.getvalue()


class CreateTests(WorktreeCase):
    def test_new_branch_starts_at_the_base_and_gets_the_bootstrap(self):
        self.write(".claude/settings.local.json", SETTINGS)
        out = self.script("create", REF, "--base", "main")
        path = self.path()
        for line in ("CASE A: a new branch from origin/main", "BASE main (from --base)", "FETCHED origin main",
                     f"MADE {path}", "UPSTREAM none", "SETTINGS copied .claude/settings.local.json",
                     f"NOTES {path / 'Notes'}"):
            self.assertIn(line, out.splitlines())
        self.ends_with(out, f"RESULT: CREATED. The worktree of {REF} is at {path}.")
        self.assertTrue(self.is_listed(path))
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=path), self.git("rev-parse", "origin/main"))
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD", cwd=path), REF)
        self.assertFalse(self.has_upstream(REF))
        self.assertTrue((path / "Notes").is_dir())
        self.assertEqual((path / ".claude" / "settings.local.json").read_text(encoding="utf-8"), SETTINGS)
        self.assertNotIn("worktrees", self.git("status", "--porcelain", "--untracked-files=all"))

    def test_plan_prints_the_steps_and_changes_nothing(self):
        self.write(".gitignore", "Notes/\n")
        self.commit_all("no rule")
        exclude = self.repo / ".git" / "info" / "exclude"
        before = exclude.read_bytes()
        out = self.script("create", REF, "--plan")
        self.assertIn("IGNORE none. No git rule ignores .claude/worktrees/", out)
        self.assertNotIn("STEP add", out)
        self.assertIn("STEP git fetch origin main", out)
        self.assertRegex(out, rf"(?m)^STEP git worktree add --no-track -b {re.escape(REF)} .+ refs/remotes/origin/main$")
        self.ends_with(out, "RESULT: READY. Nothing changed. Run again without --plan.")
        out = self.script("create", REF, "--plan", "--add-exclude")
        self.assertIn("STEP add .claude/worktrees/ to the local exclude file of git", out)
        self.assertEqual(self.branches(), ["main"])
        self.assertFalse((self.repo / ".claude").exists())
        self.assertEqual(exclude.read_bytes(), before)

    def test_base_comes_from_origin_head(self):
        out = self.script("create", REF)
        self.assertIn("BASE main (from origin/HEAD)", out)

    def test_base_starts_at_the_fetched_commit_of_origin(self):
        other = self.make_repo(self.tmp / "other")
        self.git("remote", "set-url", "origin", (self.tmp / "repo-origin.git").as_posix(), cwd=other)
        self.git("fetch", "-q", "origin", cwd=other)
        self.git("reset", "-q", "--hard", "origin/main", cwd=other)
        self.write("later.txt", "later\n", cwd=other)
        later = self.commit_all("later", cwd=other)
        self.git("push", "-q", "origin", "main", cwd=other)
        self.script("create", REF)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.path()), later)

    def test_no_base_and_no_origin_head_is_refused(self):
        self.git("remote", "set-head", "origin", "--delete")
        out = self.script("create", REF, code=3)
        self.assertIn("REFUSED: origin/HEAD is not set", out)
        self.ends_with(out, "RESULT: REFUSED. Nothing changed.")
        self.assertEqual(self.branches(), ["main"])
        self.assertFalse(os.path.lexists(self.path()))

    def test_local_branch_keeps_its_commit_and_loses_its_upstream(self):
        self.git("checkout", "-q", "-b", REF)
        self.write("src/a.txt", "a\n")
        work = self.commit_all("work")
        self.git("push", "-q", "-u", "origin", REF)
        self.git("checkout", "-q", "main")
        out = self.script("create", REF, "--base", "main")
        self.assertIn("CASE B: the local branch", out)
        self.assertIn("BASE main not used, because the branch exists", out)
        self.assertNotIn("FETCHED", out)
        self.assertIn(f"UPSTREAM removed, it was refs/heads/{REF}", out)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.path()), work)
        self.assertFalse(self.has_upstream(REF))

    def test_remote_branch_gets_a_local_branch_with_no_upstream(self):
        self.git("checkout", "-q", "-b", REF)
        self.write("src/b.txt", "b\n")
        remote = self.commit_all("remote work")
        self.git("push", "-q", "origin", REF)
        self.git("checkout", "-q", "main")
        self.git("branch", "-q", "-D", REF)
        self.git("update-ref", "-d", f"refs/remotes/origin/{REF}")
        out = self.script("create", REF)
        self.assertIn(f"CASE C: a new local branch from origin/{REF}", out)
        self.assertIn(f"FETCHED origin {REF}", out)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.path()), remote)
        self.assertFalse(self.has_upstream(REF))

    def test_remote_branch_must_match_the_whole_name(self):
        self.git("push", "-q", "origin", f"main:refs/heads/refs/heads/{REF}")
        out = self.script("create", REF)
        self.assertIn("CASE A: a new branch from origin/main", out)

    def test_no_ignore_rule_is_refused_without_add_exclude(self):
        self.write(".gitignore", "Notes/\n")
        self.commit_all("no rule")
        out = self.script("create", REF, code=3)
        self.assertIn("REFUSED: no git rule ignores .claude/worktrees/", out)
        self.assertEqual(self.branches(), ["main"])

    def test_add_exclude_writes_the_local_exclude_file_only(self):
        self.write(".gitignore", "Notes/\n")
        self.commit_all("no rule")
        exclude = self.repo / ".git" / "info" / "exclude"
        exclude.write_bytes(b"# no line end at the end")
        out = self.script("create", REF, "--add-exclude")
        self.assertIn(f"EXCLUDE added .claude/worktrees/ to {exclude}", out)
        self.assertEqual(exclude.read_bytes(), b"# no line end at the end\n.claude/worktrees/\n")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_existing_rule_names_its_source(self):
        out = self.script("create", REF, "--add-exclude")
        self.assertIn("IGNORE .claude/worktrees/ is ignored by .gitignore:1:.claude/worktrees/", out)
        self.assertNotIn("EXCLUDE", out)

    def test_existing_worktree_and_folder_are_refused(self):
        self.script("create", REF)
        out = self.script("create", REF, code=3)
        self.assertIn("REFUSED: git already lists a worktree at this path", out)
        other = "feature/other"
        self.path(other).mkdir(parents=True)
        out = self.script("create", other, code=3)
        self.assertIn("REFUSED: the folder exists, and git does not list it as a worktree", out)
        self.assertNotIn(other, self.branches())

    def test_branch_checked_out_elsewhere_is_refused(self):
        out = self.script("create", "main", code=3)
        self.assertIn("REFUSED: the branch is checked out in the worktree", out)

    def test_invalid_branch_names_are_refused(self):
        for name in ("-x", "HEAD", "@", "a..b", "x/.y", "a b", "../escape", "a@{-1}", "x.lock", "a\tb", "a/"):
            with self.subTest(name=name):
                out = self.script("create", "--", name, code=3)
                self.assertIn("is not a valid branch name", out)
        self.assertEqual(self.branches(), ["main"])
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())

    def test_name_that_git_expands_is_refused(self):
        self.git("checkout", "-q", "-b", "previous")
        self.git("checkout", "-q", "main")
        out = self.script("create", "@{-1}", code=3)
        self.assertIn("REFUSED: the branch @{-1} is not a valid branch name", out)
        self.assertFalse((self.repo / ".claude" / "worktrees").exists())

    def test_link_out_of_the_worktree_folder_is_refused(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        link = self.repo / ".claude" / "worktrees" / "team"
        link.parent.mkdir(parents=True)
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"no right to make a link: {error}")
        out = self.script("create", "team/x", code=3)
        self.assertIn("is outside .claude/worktrees/", out)
        self.assertEqual(list(outside.iterdir()), [])

    def test_invalid_base_is_refused(self):
        out = self.script("create", REF, "--base", "a..b", code=3)
        self.assertIn("REFUSED: the base a..b is not a valid branch name", out)

    def test_notes_folder_must_stay_inside_the_worktree(self):
        for value in ("../x", "a/../../x", str(self.tmp / "abs"), "", "."):
            with self.subTest(value=value):
                result = run([sys.executable, "-I", SCRIPT, "create", REF, "--notes-dir", value], cwd=self.repo)
                self.assertResult(result, 2, "not a relative folder inside the worktree")
        out = self.script("create", REF, "--notes-dir", "docs/notes")
        self.assertTrue((self.path() / "docs" / "notes").is_dir())
        self.assertIn(f"NOTES {self.path() / 'docs' / 'notes'}", out)

    def test_settings_file_of_the_branch_stays(self):
        self.git("checkout", "-q", "-b", REF)
        self.write(".claude/settings.local.json", "branch\n")
        self.git("add", "-f", ".claude/settings.local.json")
        self.git("commit", "-q", "-m", "tracked settings")
        self.git("checkout", "-q", "main")
        self.write(".claude/settings.local.json", "main\n")
        out = self.script("create", REF)
        self.assertIn("SETTINGS the branch has its own .claude/settings.local.json, so it stays", out)
        self.assertEqual((self.path() / ".claude" / "settings.local.json").read_text(encoding="utf-8"), "branch\n")

    def test_settings_file_that_git_does_not_ignore_is_not_copied(self):
        self.write(".gitignore", ".claude/worktrees/\n")
        self.commit_all("no settings rule")
        self.git("push", "-q", "origin", "main")
        self.write(".claude/settings.local.json", SETTINGS)
        out = self.script("create", REF)
        self.assertIn("SETTINGS not copied: git does not ignore .claude/settings.local.json", out)
        self.assertFalse(os.path.lexists(self.path() / ".claude" / "settings.local.json"))
        self.assertIn("RESULT: READY", self.script("remove", REF))

    def test_no_settings_file_in_the_main_worktree(self):
        out = self.script("create", REF)
        self.assertIn("SETTINGS none in the main worktree", out)

    def test_failed_worktree_add_names_what_it_left(self):
        (self.repo / ".git" / "worktrees").write_bytes(b"not a folder")
        out = self.script("create", REF, code=1)
        self.assertRegex(out, r"(?m)^FAILED git worktree add: .+")
        self.assertRegex(out, rf"(?m)^LEFT branch {re.escape(REF)} at [0-9a-f]{{12}}, made by git worktree add -b")
        self.ends_with(out, "RESULT: FAILED. No worktree was made.")
        self.assertNotIn("MADE", out)

    def test_failed_add_of_a_local_branch_leaves_no_branch_line(self):
        self.git("branch", REF)
        (self.repo / ".git" / "worktrees").write_bytes(b"not a folder")
        out = self.script("create", REF, code=1)
        self.assertNotIn("LEFT branch", out)
        self.ends_with(out, "RESULT: FAILED. No worktree was made.")

    def test_failed_ls_remote_changes_nothing(self):
        self.git("remote", "set-url", "origin", (self.tmp / "missing.git").as_posix())
        out = self.script("create", REF, code=1)
        self.assertRegex(out, r"(?m)^FAILED git ls-remote: .+")
        self.ends_with(out, "RESULT: FAILED. Nothing changed.")
        self.assertEqual(self.branches(), ["main"])

    def test_failed_fetch_makes_no_worktree(self):
        real = wt.git_result

        def fake(cwd, *args):
            if args[0] == "fetch":
                return 128, "", "fatal: the network is down"
            return real(cwd, *args)

        with mock.patch.object(wt, "git_result", fake):
            code, out = self.in_process("create", REF, "--repo", self.repo)
        self.assertEqual(code, 1, out)
        self.assertIn("FAILED git fetch: fatal: the network is down", out)
        self.ends_with(out, "RESULT: FAILED. No worktree was made.")
        self.assertFalse(self.is_listed(self.path()))

    def test_failed_bootstrap_step_keeps_the_worktree(self):
        self.write("Notes", "a file where the notes folder goes\n")
        self.write(".gitignore", ".claude/worktrees/\n")
        self.commit_all("a file named Notes")
        self.git("push", "-q", "origin", "main")
        out = self.script("create", REF, code=1)
        self.assertRegex(out, r"(?m)^FAILED the notes folder: ")
        self.assertIn("RESULT: CREATED, BUT 1 BOOTSTRAP STEPS FAILED.", out)
        self.assertTrue(self.is_listed(self.path()))

    def test_repository_path_with_a_space_and_non_ascii_letters(self):
        self.repo = self.make_repo(self.tmp / "my répo")
        out = self.script("create", REF)
        self.assertIn("my répo", out)
        self.assertTrue(self.is_listed(self.path()))

    def test_run_from_a_linked_worktree_uses_the_main_worktree(self):
        self.script("create", REF)
        out = self.script("create", "feature/second", cwd=self.path())
        self.assertIn(f"MADE {self.path('feature/second')}", out)
        self.assertFalse((self.path() / ".claude" / "worktrees").exists())

    def test_git_gets_no_input_and_no_terminal_prompt(self):
        with mock.patch.object(subprocess, "run") as fake:
            fake.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            wt.git_result(self.repo, "fetch", "origin")
        self.assertEqual(fake.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(fake.call_args.kwargs["stdin"], subprocess.DEVNULL)


class RemoveTests(WorktreeCase):
    def setUp(self):
        super().setUp()
        self.script("create", REF)

    def test_plan_changes_nothing(self):
        out = self.script("remove", REF)
        self.assertIn("MODE REMOVE PLAN: nothing changes", out)
        self.assertIn(f"BRANCH {REF}", out)
        self.assertIn(f"STEP git worktree remove {self.path()}", out)
        self.ends_with(out, "RESULT: READY. Nothing changed. Run again with the same arguments and --apply.")
        self.assertTrue(self.is_listed(self.path()))

    def test_apply_removes_the_worktree_and_keeps_the_branch(self):
        self.write("src/c.txt", "c\n", cwd=self.path())
        work = self.commit_all("work", cwd=self.path())
        out = self.script("remove", REF, "--apply")
        self.assertIn(f"REMOVED {self.path()}", out)
        self.ends_with(out, f"RESULT: REMOVED. The branch {REF} and its commits stay.")
        self.assertFalse(os.path.lexists(self.path()))
        self.assertFalse(self.is_listed(self.path()))
        self.assertEqual(self.git("rev-parse", REF), work)

    def test_detached_worktree_names_no_branch(self):
        self.git("checkout", "-q", "--detach", cwd=self.path())
        out = self.script("remove", REF, "--apply")
        self.assertIn("BRANCH none (detached HEAD)", out)
        self.ends_with(out, "RESULT: REMOVED. The branch (none) and its commits stay.")

    def test_changes_are_refused_in_both_modes(self):
        self.write("new.txt", "untracked\n", cwd=self.path())
        self.write("README.md", "changed\n", cwd=self.path())
        for extra in ((), ("--apply",)):
            with self.subTest(apply=bool(extra)):
                out = self.script("remove", REF, *extra, code=3)
                self.assertIn("CHANGED  M README.md", out)
                self.assertIn("CHANGED ?? new.txt", out)
                self.assertIn("REFUSED: the worktree has changes or untracked files: 2.", out)
                self.assertNotIn("STEP", out)
        self.assertTrue(self.is_listed(self.path()))
        self.assertEqual((self.path() / "new.txt").read_text(encoding="utf-8"), "untracked\n")

    def test_ignored_files_are_named_before_the_removal(self):
        self.write("Notes/plan.md", "plan\n", cwd=self.path())
        out = self.script("remove", REF)
        self.assertIn("IGNORED Notes/", out.splitlines())
        self.assertIn("RESULT: READY", out)

    def test_missing_folder_is_removed_without_force(self):
        shutil.rmtree(self.path())
        out = self.script("remove", REF, "--apply")
        self.assertIn("FOLDER missing. git still lists the worktree", out)
        self.assertIn("RESULT: REMOVED", out)
        self.assertFalse(self.is_listed(self.path()))

    def test_locked_worktree_is_refused(self):
        self.git("worktree", "lock", "--reason", "on a disk", str(self.path()))
        out = self.script("remove", REF, "--apply", code=3)
        self.assertIn("REFUSED: the worktree is locked (on a disk). Run git worktree unlock first", out)
        self.assertTrue(self.is_listed(self.path()))

    def test_folder_that_git_does_not_list_is_kept(self):
        orphan = self.path("feature/orphan")
        orphan.mkdir(parents=True)
        (orphan / "draft.md").write_bytes(b"draft\n")
        out = self.script("remove", "feature/orphan", "--apply", code=3)
        self.assertIn("REFUSED: git does not list this folder as a worktree. The script does not delete it", out)
        self.assertTrue((orphan / "draft.md").is_file())

    def test_unknown_branch_is_refused(self):
        out = self.script("remove", "feature/none", "--apply", code=3)
        self.assertIn("REFUSED: no worktree is at this path", out)

    def test_worktree_outside_the_folder_is_never_removed(self):
        outside = self.tmp / "outside"
        self.git("worktree", "add", "-q", "-b", "feature/outside", str(outside), "main")
        out = self.script("remove", "feature/outside", "--apply", code=3)
        self.assertIn("REFUSED: no worktree is at this path", out)
        self.assertTrue(self.is_listed(outside))

    def test_run_from_inside_the_worktree_is_refused(self):
        for folder in (self.path(), self.path() / "Notes"):
            with self.subTest(folder=folder):
                out = self.script("remove", REF, "--apply", code=3, cwd=folder)
                self.assertIn("REFUSED: the current folder is inside the worktree", out)
        self.assertTrue(self.is_listed(self.path()))

    def test_failed_removal_names_what_is_left(self):
        real = wt.git_result
        calls = []

        def fake(cwd, *args):
            if args[:2] == ("worktree", "remove"):
                calls.append(args)
                return 128, "", "fatal: Permission denied"
            return real(cwd, *args)

        with mock.patch.object(wt, "git_result", fake):
            code, out = self.in_process("remove", REF, "--apply", "--repo", self.repo)
        self.assertEqual(code, 1, out)
        self.assertEqual(calls, [("worktree", "remove", str(self.path()))])
        self.assertIn("FAILED git worktree remove: fatal: Permission denied", out)
        self.assertIn(f"LEFT folder {self.path()}", out)
        self.assertIn(f"LEFT worktree {self.path()}, which git lists", out)
        self.ends_with(out, "RESULT: FAILED. Read the LEFT lines.")

    def test_output_is_short_for_an_agent(self):
        for number in range(wt.MAX_PATHS + 5):
            self.write(f"new{number:02}.txt", "x\n", cwd=self.path())
        out = self.script("remove", REF, code=3)
        self.assertEqual(out.count("CHANGED ?? new"), wt.MAX_PATHS)
        self.assertIn("CHANGED ... 5 more", out)
        with mock.patch.object(wt, "LINE_CHARS", 60):
            code, out = self.in_process("remove", REF, "--repo", self.repo)
        self.assertEqual(code, 3, out)
        self.assertIn("more characters", out)
        self.assertTrue(all(len(line) <= 60 + 30 for line in out.splitlines()), out)


class PruneTests(WorktreeCase):
    def test_nothing_to_prune(self):
        out = self.script("prune", "--apply")
        self.ends_with(out, "RESULT: NOTHING TO PRUNE. Nothing changed.")

    def test_plan_lists_the_stale_entry_and_apply_prunes_it(self):
        self.script("create", REF)
        shutil.rmtree(self.path())
        out = self.script("prune")
        self.assertRegex(out, rf"(?m)^PRUNE {re.escape(str(self.path()))} \(.+\)$")
        self.assertIn("STEP git worktree prune", out)
        self.ends_with(out, "RESULT: READY. Nothing changed. Run again with the same arguments and --apply.")
        self.assertTrue(self.is_listed(self.path()))
        out = self.script("prune", "--apply")
        self.ends_with(out, "RESULT: PRUNED. git no longer lists 1 worktrees.")
        self.assertFalse(self.is_listed(self.path()))
        self.assertIn(REF, self.branches())

    def test_stale_entry_outside_the_folder_is_refused(self):
        self.script("create", REF)
        shutil.rmtree(self.path())
        for number, outside in enumerate((self.tmp / "outside", self.repo / "build" / "wt")):
            with self.subTest(outside=outside):
                self.git("worktree", "add", "-q", "-b", f"feature/outside-{number}", str(outside), "main")
                shutil.rmtree(outside)
                for extra in ((), ("--apply",)):
                    out = self.script("prune", *extra, code=3)
                    self.assertIn(f"REFUSED: the entry {outside} is outside .claude/worktrees/", out)
                    self.assertNotIn("STEP", out)
                self.assertTrue(self.is_listed(outside))
                self.git("worktree", "remove", str(outside))
        self.assertTrue(self.is_listed(self.path()))

    def test_locked_stale_entry_is_not_pruned(self):
        self.script("create", REF)
        self.git("worktree", "lock", str(self.path()))
        shutil.rmtree(self.path())
        out = self.script("prune", "--apply")
        self.assertIn("RESULT: NOTHING TO PRUNE", out)
        self.assertTrue(self.is_listed(self.path()))


class SetupTests(WorktreeCase):
    def test_a_subcommand_is_needed(self):
        result = run([sys.executable, "-I", SCRIPT], cwd=self.repo)
        self.assertResult(result, 2, "usage:")

    def test_folder_outside_a_repository_is_a_setup_error(self):
        folder = self.tmp / "plain"
        folder.mkdir()
        result = run([sys.executable, "-I", SCRIPT, "prune", "--repo", folder])
        self.assertResult(result, 2, "error: not inside a git repository")

    def test_bare_repository_is_a_setup_error(self):
        result = run([sys.executable, "-I", SCRIPT, "prune", "--repo", self.tmp / "repo-origin.git"])
        self.assertResult(result, 2, "error: a bare repository has no main worktree")

    def test_old_git_is_a_setup_error(self):
        real = wt.git_result
        for version, code in (("2.30.9", 2), ("2.31.0", 0), ("3.0.0", 0)):
            def fake(cwd, *args, version=version):
                if args == ("version",):
                    return 0, f"git version {version}\n", ""
                return real(cwd, *args)

            with self.subTest(version=version), mock.patch.object(wt, "git_result", fake):
                self.assertEqual(self.in_process("prune", "--repo", self.repo)[0], code)

    def test_inside_compares_real_paths(self):
        self.assertTrue(wt.inside(self.repo / "a" / "b", self.repo / "a"))
        self.assertFalse(wt.inside(self.repo / "a", self.repo / "a"))
        self.assertFalse(wt.inside(self.repo / "ab", self.repo / "a"))
        self.assertFalse(wt.inside(self.repo / "a" / ".." / "b", self.repo / "a"))
        if os.name == "nt":
            self.assertFalse(wt.inside(Path("D:/x"), Path("C:/x")))


if __name__ == "__main__":
    unittest.main()
