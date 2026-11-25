"""Tests for essentials/dev-essentials/scripts/backup_move.py.

Each test builds a git workspace and a backup root in a temporary folder and
runs the script as a child process, as the save-context command does.
"""
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from support import REPO, tool_missing
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/scripts/backup_move.py"


class BackupMoveCase(ScratchCase):
    def setUp(self):
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        super().setUp()
        self.ws = self.tmp / "ws"
        self.ws.mkdir()
        git_init(self.ws)
        self.backup = self.tmp / "backup"

    def write(self, rel, content="note\n"):
        path = self.ws / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def track(self, rel):
        subprocess.run(["git", "-C", str(self.ws), "add", "--", rel], check=True, capture_output=True)

    def run_script(self, *args, env=None):
        return run([sys.executable, "-I", SCRIPT, *args], env=env)

    def run_move(self, *args):
        return self.run_script("--workspace", self.ws, "--backup", self.backup, *args)


class PlanAndApplyTests(BackupMoveCase):
    def test_plan_moves_nothing(self):
        self.write("Notes/Plans/old-plan.md")
        result = self.run_move("Notes/Plans/old-plan.md")
        self.assertResult(result, 0, "MOVE Notes/Plans/old-plan.md", "RESULT: PLAN 1")
        self.assertTrue((self.ws / "Notes/Plans/old-plan.md").is_file())
        self.assertFalse(self.backup.exists())

    def test_apply_moves_the_file_and_keeps_its_relative_path(self):
        self.write("Notes/Plans/old-plan.md", "plan text\n")
        self.write("Notes/_progress.md")
        result = self.run_move("--apply", "Notes/Plans/old-plan.md", self.ws / "Notes/_progress.md")
        self.assertResult(result, 0, "MOVED Notes/Plans/old-plan.md", "MOVED Notes/_progress.md", "RESULT: MOVED 2")
        self.assertFalse((self.ws / "Notes/Plans/old-plan.md").exists())
        self.assertEqual((self.backup / "Notes/Plans/old-plan.md").read_text(encoding="utf-8"), "plan text\n")
        self.assertTrue((self.backup / "Notes/_progress.md").is_file())

    def test_default_backup_folder_is_under_the_home_folder(self):
        self.write("Notes/old.md")
        home = self.tmp / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
        result = self.run_script("--workspace", self.ws, "Notes/old.md", env=env)
        self.assertResult(result, 0, "RESULT: PLAN 1")
        line = next(l for l in result.stdout.splitlines() if l.startswith("BACKUP "))
        backup = Path(line[len("BACKUP "):])
        self.assertEqual(backup.parent, (home / "save-context-backups").resolve())
        self.assertTrue(backup.name.startswith("ws-"), backup.name)


class RefusalTests(BackupMoveCase):
    def test_tracked_file_is_refused_and_no_file_moves(self):
        self.write("tracked.md")
        self.track("tracked.md")
        self.write("untracked.md")
        result = self.run_move("--apply", "tracked.md", "untracked.md")
        self.assertResult(result, 1, "REFUSE tracked.md: git tracks it", "RESULT: REFUSED 1. No file moved.")
        self.assertTrue((self.ws / "tracked.md").is_file())
        self.assertTrue((self.ws / "untracked.md").is_file())
        self.assertFalse(self.backup.exists())

    def test_bad_paths_are_refused(self):
        self.write("Notes/a.md")
        (self.ws / "Notes/folder").mkdir()
        outside = self.tmp / "outside.md"
        outside.write_text("x\n", encoding="utf-8")
        result = self.run_move("missing.md", "Notes/folder", outside, "Notes/a.md", "Notes/a.md")
        self.assertResult(result, 1, "REFUSE missing.md: does not exist",
                          "REFUSE Notes/folder: is not a regular file",
                          "is outside the workspace", "REFUSE Notes/a.md: comes twice", "RESULT: REFUSED 4")

    def test_existing_target_is_refused(self):
        self.write("Notes/a.md")
        (self.backup / "Notes").mkdir(parents=True)
        (self.backup / "Notes/a.md").write_text("older copy\n", encoding="utf-8")
        result = self.run_move("--apply", "Notes/a.md")
        self.assertResult(result, 1, "REFUSE Notes/a.md: exists in the backup folder")
        self.assertEqual((self.backup / "Notes/a.md").read_text(encoding="utf-8"), "older copy\n")

    def test_symbolic_link_is_refused(self):
        target = self.write("real.md")
        link = self.ws / "link.md"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("this system cannot make a symbolic link")
        result = self.run_move("link.md")
        self.assertResult(result, 1, "REFUSE link.md: is a symbolic link")


class UsageTests(BackupMoveCase):
    def test_backup_inside_the_workspace_is_a_usage_error(self):
        self.write("a.md")
        result = self.run_script("--workspace", self.ws, "--backup", self.ws / "backup", "a.md")
        self.assertResult(result, 2, "must not contain each other")

    def test_backup_that_contains_the_workspace_is_a_usage_error(self):
        self.write("a.md")
        result = self.run_script("--workspace", self.ws, "--backup", self.tmp, "a.md")
        self.assertResult(result, 2, "must not contain each other")

    def test_workspace_outside_git_moves_the_file(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        (plain / "a.md").write_text("x\n", encoding="utf-8")
        result = self.run_script("--workspace", plain, "--backup", self.backup, "--apply", "a.md")
        self.assertResult(result, 0, "MOVED a.md", "RESULT: MOVED 1")
        self.assertTrue((self.backup / "a.md").is_file())
        self.assertFalse((plain / "a.md").exists())


if __name__ == "__main__":
    unittest.main()
