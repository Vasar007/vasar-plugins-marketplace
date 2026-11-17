"""Tests for essentials/dev-essentials/scripts/merge_projects.py.

Each test builds a projects folder in a temporary folder and runs the script as a child process, as the
command merge-worktree-projects does. The files get a modification time of 3 days ago, so that the check
for recent activity passes, unless a test wants a recent file.
"""
import os
import re
import shutil
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

from support import REPO, load_module
from testkit import ScratchCase, clean_env, run

SCRIPT = REPO / "essentials/dev-essentials/scripts/merge_projects.py"
MAIN = "C--src-app"
WT1 = MAIN + "--claude-worktrees-feature-a"
WT2 = MAIN + "--claude-worktrees-feature-b"
mp = load_module("merge_projects", SCRIPT)
S1 = "11111111-1111-4111-8111-111111111111"
S2 = "22222222-2222-4222-8222-222222222222"
S3 = "33333333-3333-4333-8333-333333333333"
OLD = time.time() - 3 * 24 * 60 * 60
# Runs the script, with an os.rename that fails for one file name: python -I -c FAIL_RENAME <name> <script> <args>.
FAIL_RENAME = (
    "import os, runpy, sys\n"
    "real, name = os.rename, sys.argv[1]\n"
    "def rename(source, target):\n"
    "    if os.path.basename(source) == name:\n"
    "        raise PermissionError(13, 'another process holds the file', source)\n"
    "    real(source, target)\n"
    "os.rename = rename\n"
    "sys.argv = sys.argv[2:]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)


def make_dir_link(target, link):
    """A link to a folder: a symbolic link on Linux, a junction on Windows (no admin right needed)."""
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(str(target), str(link))


class MergeCase(ScratchCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "projects"
        (self.root / MAIN).mkdir(parents=True)

    def write(self, rel, text="x\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def age(self, when=OLD):
        """Give each file and folder below the root the modification time when.

        Windows cannot set the time of a link itself, so a test with a link passes --allow-recent there.
        """
        for top, dirs, files in os.walk(str(self.root)):
            for name in dirs + files:
                path = os.path.join(top, name)
                if os.name != "nt":
                    os.utime(path, (when, when), follow_symlinks=False)
                elif not os.path.islink(path) and not os.path.isjunction(path):
                    os.utime(path, (when, when))

    def tree(self):
        """Each path below the root with its bytes (None for a folder) and its modification time."""
        result = {}
        for top, dirs, files in os.walk(str(self.root)):
            for name in dirs + files:
                path = os.path.join(top, name)
                rel = os.path.relpath(path, str(self.root)).replace(os.sep, "/")
                data = None if name in dirs else Path(path).read_bytes()
                result[rel] = (data, os.lstat(path).st_mtime_ns)
        return result

    def merge(self, *args, env=None):
        return run([sys.executable, "-I", SCRIPT, "--root", self.root, *args], env=env)

    def code(self, result):
        return re.search(r"^PLAN ([0-9a-f]{12})$", result.stdout, re.M).group(1)

    def dry_then_apply(self, *args):
        dry = self.merge(*args)
        self.assertResult(dry, 0, "DRY RUN")
        flags, dashes, keywords = [], False, []
        for arg in args:
            dashes = dashes or arg == "--"
            (keywords if dashes else flags).append(arg)
        applied = self.merge(*flags, "--apply", "--confirm", self.code(dry), *keywords)
        self.assertResult(applied, 0, "RESULT: APPLIED")
        return dry, applied

    def apply_with_a_failed_move(self, code, name):
        """Run the apply run while the move of the file name in WT1 fails.

        On Windows, the test holds the file open, so the rename fails for real. On Linux, a test can run as
        root, and root can rename into a read-only folder. So there, a wrapper makes os.rename fail.
        """
        if os.name == "nt":
            with open(self.root / WT1 / name, "rb"):
                return self.merge("--apply", "--confirm", code)
        return run([sys.executable, "-I", "-c", FAIL_RENAME, os.path.basename(name), SCRIPT, "--root", self.root,
                    "--apply", "--confirm", code])

    def sessions(self, folder, *ids, subagents=False):
        for sid in ids:
            self.write(f"{folder}/{sid}.jsonl", f'{{"session":"{sid}"}}\n')
            if subagents:
                self.write(f"{folder}/{sid}/subagents/agent-1.jsonl", "{}\n")


class DryRunTests(MergeCase):
    def test_dry_run_changes_nothing_and_prints_the_plan(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2, subagents=True)
        self.write(f"{WT1}/memory/new.md", "new\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [New](new.md) - a new fact\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md) - an old fact\n")
        self.age()
        before = self.tree()
        result = self.merge()
        self.assertResult(result, 0, "DRY RUN: no file was moved", f"MAIN {MAIN}: 1 worktree folders",
                          f"MOVE {WT1}: 2 entries to the main folder (1 files, 1 folders)",
                          f"INDEX {WT1}: 1 lines are appended to {MAIN}/memory/MEMORY.md",
                          "INDEX LINE - [New](new.md) - a new fact", f"DELETE {WT1}",
                          "TOTAL: 1 pairs merge, 2 entries move, 1 folders are deleted", "--apply --confirm")
        self.assertEqual(self.tree(), before)

    def test_projects_folder_with_no_worktree_folder_has_an_empty_plan(self):
        self.sessions(MAIN, S1)
        self.age()
        result = self.merge()
        self.assertResult(result, 0, "TOTAL: 0 pairs merge, 0 entries move, 0 folders are deleted")
        self.assertNotIn("MAIN", result.stdout)

    def test_main_folder_named_with_no_worktree_folder_says_so(self):
        self.sessions(MAIN, S1)
        self.age()
        self.assertResult(self.merge("src-app"), 0, f"MAIN {MAIN}: no worktree folder")


class ApplyTests(MergeCase):
    def test_apply_moves_the_sessions_and_deletes_the_empty_folder(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2, subagents=True)
        self.sessions(WT2, S3)
        self.age()
        self.dry_then_apply()
        self.assertEqual(sorted(os.listdir(self.root)), [MAIN])
        self.assertEqual(sorted(os.listdir(self.root / MAIN)), sorted([f"{S1}.jsonl", f"{S2}.jsonl", S2, f"{S3}.jsonl"]))
        self.assertTrue((self.root / MAIN / S2 / "subagents" / "agent-1.jsonl").is_file())

    def test_empty_worktree_folder_is_deleted(self):
        self.sessions(MAIN, S1)
        (self.root / WT1).mkdir()
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"NOTE {WT1}: the folder is empty", dry.stdout)
        self.assertFalse((self.root / WT1).exists())

    def test_apply_needs_the_code_of_the_approved_plan(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        before = self.tree()
        self.assertResult(self.merge("--apply"), 2, "--apply needs --confirm")
        self.assertResult(self.merge("--confirm", "abc"), 2, "--confirm works only with --apply")
        self.assertResult(self.merge("--apply", "--confirm", "000000000000"), 4, "RESULT: PLAN CHANGED")
        code = self.code(self.merge())
        near = code[:-1] + ("1" if code[-1] == "0" else "0")
        self.assertResult(self.merge("--apply", "--confirm", near), 4, "RESULT: PLAN CHANGED")
        self.assertEqual(self.tree(), before)

    def test_plan_that_changed_after_the_dry_run_is_refused(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        dry = self.merge()
        self.sessions(WT1, S3)
        self.age()
        before = self.tree()
        self.assertResult(self.merge("--apply", "--confirm", self.code(dry)), 4, "RESULT: PLAN CHANGED")
        self.assertEqual(self.tree(), before)

    def test_second_run_after_a_full_merge_has_nothing_to_do(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        self.dry_then_apply()
        before = self.tree()
        self.assertResult(self.merge(), 0, "TOTAL: 0 pairs merge")
        self.assertEqual(self.tree(), before)

    def test_second_run_after_a_partial_merge_changes_nothing_more(self):
        for n in [""] + [f"-{i}" for i in range(2, 10)]:
            self.write(f"{MAIN}/memory/note{n}.md", f"main {n}\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Note](note.md)\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/other.md", "other\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Note](note.md)\n- [Other](other.md)\n")
        self.sessions(WT1, S2)
        self.age()
        self.dry_then_apply()
        self.age()
        before = self.tree()
        dry, applied = self.dry_then_apply()
        self.assertIn(f"KEEP {WT1}: not empty after the merge, it still holds memory", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_failed_move_stops_the_run_and_deletes_nothing(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2, S3)
        self.age()
        dry = self.merge()
        result = self.apply_with_a_failed_move(self.code(dry), f"{S3}.jsonl")
        self.assertResult(result, 1, f"FAILED move {WT1}/{S3}.jsonl {MAIN}/{S3}.jsonl",
                          "RESULT: FAILED. The run stopped at the first failed action")
        self.assertTrue((self.root / MAIN / f"{S2}.jsonl").is_file())
        self.assertTrue((self.root / WT1 / f"{S3}.jsonl").is_file())
        self.assertEqual(os.listdir(self.root / WT1), [f"{S3}.jsonl"])

    def test_failed_line_prints_a_name_with_a_line_break_as_one_line(self):
        # U+2028 is a line separator that Windows allows in a file name. Linux also allows a real line break.
        name = S3 + (" " if os.name == "nt" else "\n") + "RESULT: APPLIED 000000000000.jsonl"
        self.write(f"{WT1}/{name}", "{}\n")
        self.age()
        dry = self.merge()
        result = self.apply_with_a_failed_move(self.code(dry), name)
        self.assertResult(result, 1, "FAILED move")
        lines = result.stdout.splitlines()
        self.assertEqual([l for l in lines if l.startswith("RESULT:")],
                         ["RESULT: FAILED. The run stopped at the first failed action. Run a dry run again."])
        failed = next(l for l in lines if l.startswith("FAILED move"))
        self.assertIn("\\u2028" if os.name == "nt" else "\\n", failed)


class MemoryTests(MergeCase):
    def test_new_file_moves_and_a_file_with_the_same_bytes_is_dropped(self):
        self.write(f"{MAIN}/memory/same.md", "same\n")
        self.write(f"{WT1}/memory/same.md", "same\n")
        self.write(f"{WT1}/memory/new.md", "new\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"MEMORY {WT1}: 1 files move, 1 files with the same bytes", dry.stdout)
        self.assertEqual(sorted(os.listdir(self.root / MAIN / "memory")), ["new.md", "same.md"])
        self.assertFalse((self.root / WT1).exists())

    def test_file_with_other_bytes_gets_the_first_free_number_and_its_index_line(self):
        self.write(f"{MAIN}/memory/note.md", "main\n")
        self.write(f"{MAIN}/memory/note-2.md", "main 2\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "# Index\n- [Note](note.md)\n- [Note 2](note-2.md)\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "# Index\n- [Note](note.md) - from the worktree\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"MEMORY {WT1}: note.md moves as note-3.md, it needs a manual merge or review", dry.stdout)
        self.assertEqual((self.root / MAIN / "memory/note-3.md").read_text(encoding="utf-8"), "worktree\n")
        self.assertEqual((self.root / MAIN / "memory/note.md").read_text(encoding="utf-8"), "main\n")
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_text(encoding="utf-8"),
                         "# Index\n- [Note](note.md)\n- [Note 2](note-2.md)\n- [Note](note-3.md) - from the worktree\n")

    def test_no_free_name_keeps_the_file_and_the_index_of_the_worktree(self):
        for n in [""] + [f"-{i}" for i in range(2, 10)]:
            self.write(f"{MAIN}/memory/note{n}.md", f"main {n}\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Main](note.md)\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Note](note.md)\n")
        self.sessions(WT1, S2)
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"MEMORY {WT1}: note.md stays, no free name up to note-9.md", dry.stdout)
        self.assertIn(f"INDEX {WT1}: keeps its index", dry.stdout)
        self.assertEqual(sorted(os.listdir(self.root / WT1 / "memory")), ["MEMORY.md", "note.md"])
        self.assertEqual(os.listdir(self.root / WT1), ["memory"])
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_text(encoding="utf-8"), "- [Main](note.md)\n")
        self.assertTrue((self.root / MAIN / f"{S2}.jsonl").is_file())

    def test_index_of_the_main_folder_is_made_from_a_top_level_index(self):
        self.sessions(MAIN, S1)
        self.write(f"{WT1}/MEMORY.md", "# Memory\n- [Fact](fact.md)\n")
        self.write(f"{WT1}/memory/fact.md", "fact\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"INDEX {WT1}: creates {MAIN}/memory/MEMORY.md from {WT1}/MEMORY.md, 2 lines", dry.stdout)
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_text(encoding="utf-8"),
                         "# Memory\n- [Fact](fact.md)\n")
        self.assertFalse((self.root / WT1).exists())

    def test_index_appends_only_the_lines_that_the_main_index_does_not_name(self):
        self.write(f"{MAIN}/MEMORY.md", "- [A](a.md)")
        self.write(f"{WT1}/memory/MEMORY.md", "# Index\n- [A](a.md) - again\n- [B](b.md)\r\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"INDEX {WT1}: 1 lines are appended to {MAIN}/MEMORY.md", dry.stdout)
        self.assertEqual((self.root / MAIN / "MEMORY.md").read_bytes(), b"- [A](a.md)\r\n- [B](b.md)\r\n")
        self.assertFalse((self.root / MAIN / "memory").exists())

    def test_two_worktree_folders_with_the_same_name_get_two_numbers(self):
        self.write(f"{MAIN}/memory/note.md", "main\n")
        self.write(f"{WT1}/memory/note.md", "one\n")
        self.write(f"{WT2}/memory/note.md", "two\n")
        self.age()
        self.dry_then_apply()
        memory = self.root / MAIN / "memory"
        self.assertEqual(sorted(os.listdir(memory)), ["note-2.md", "note-3.md", "note.md"])
        self.assertEqual((memory / "note-3.md").read_text(encoding="utf-8"), "two\n")

    def test_made_index_marks_the_line_of_a_file_that_stays(self):
        for n in [""] + [f"-{i}" for i in range(2, 10)]:
            self.write(f"{MAIN}/memory/note{n}.md", f"main {n}\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Note](note.md)\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_text(encoding="utf-8"),
                         "- [Note](note.md) (not migrated, see manual resolution)\n")
        self.assertEqual(os.listdir(self.root / WT1 / "memory"), ["note.md"])

    def test_folder_inside_the_memory_folder_stays(self):
        self.write(f"{WT1}/memory/old-sweep/a.md", "a\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"MEMORY {WT1}: old-sweep stays, it is a folder", dry.stdout)
        self.assertTrue((self.root / WT1 / "memory/old-sweep/a.md").is_file())


class GuardTests(MergeCase):
    def test_session_name_in_both_folders_stops_the_pair(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S1, S2)
        self.write(f"{WT1}/memory/new.md", "new\n")
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"STOP {WT1}: the main folder has an entry with the same name: {S1}.jsonl", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_recent_activity_skips_the_folder_until_the_user_allows_it(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        os.utime(self.root / WT1 / f"{S2}.jsonl")
        before = self.tree()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"SKIP {WT1}: recent activity, the newest change is 0 minutes old", dry.stdout)
        self.assertEqual(self.tree(), before)
        self.dry_then_apply("--allow-recent", WT1)
        self.assertFalse((self.root / WT1).exists())

    def test_excluded_worktree_folder_is_not_read(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S1)
        self.sessions(WT2, S2)
        self.age()
        dry, _ = self.dry_then_apply("--exclude=FEATURE-A")
        self.assertIn(f"EXCLUDED {MAIN}: 1 worktree folders: {WT1}", dry.stdout)
        self.assertNotIn("STOP", dry.stdout)
        self.assertTrue((self.root / WT1 / f"{S1}.jsonl").is_file())
        self.assertFalse((self.root / WT2).exists())

    def test_group_of_118_worktree_folders_applies_after_one_exclude_for_most_of_them(self):
        self.sessions(MAIN, S1)
        for i in range(117):
            self.sessions(f"{MAIN}--claude-worktrees-x{i:03}", S2)
        self.sessions(f"{MAIN}--claude-worktrees-y000", S3)
        self.age()
        self.assertResult(self.merge("--", MAIN), 0, "RESULT: CUT PLAN")
        dry, _ = self.dry_then_apply("--exclude=-x", "--", MAIN)
        excluded = re.findall(r"^EXCLUDED .*$", dry.stdout, re.M)
        self.assertEqual(len(excluded), 1)
        self.assertRegex(excluded[0], r"^.{200} \.\.\. \d+ more characters$")
        self.assertEqual(len(os.listdir(self.root)), 118)
        self.assertTrue((self.root / MAIN / f"{S3}.jsonl").is_file())

    def test_excluded_main_folder_skips_the_whole_group(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply("--exclude", "other,src-app")
        self.assertIn(f"EXCLUDED {MAIN}: the main folder, so the whole group is skipped", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_link_in_the_worktree_folder_stops_the_pair(self):
        outside = self.tmp / "outside"
        (outside / "memory").mkdir(parents=True)
        (outside / "memory" / "secret.md").write_text("outside\n", encoding="utf-8")
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        make_dir_link(outside / "memory", self.root / WT1 / "memory")
        self.age()
        dry, _ = self.dry_then_apply("--allow-recent", WT1)
        self.assertIn(f"STOP {WT1}: it holds a link, and the script never follows a link: memory", dry.stdout)
        self.assertTrue((outside / "memory" / "secret.md").is_file())
        self.assertTrue((self.root / WT1 / f"{S2}.jsonl").is_file())

    def test_worktree_folder_that_is_a_link_is_skipped(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / f"{S2}.jsonl").write_text("{}\n", encoding="utf-8")
        self.sessions(MAIN, S1)
        make_dir_link(outside, self.root / WT1)
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"SKIP {WT1}: the folder is a link", dry.stdout)
        self.assertTrue((outside / f"{S2}.jsonl").is_file())

    def test_folder_that_is_not_empty_after_the_merge_is_never_deleted(self):
        self.write(f"{WT1}/memory/MEMORY.md", "- [A](a.md)\n")
        self.write(f"{WT1}/MEMORY.md", "- [B](b.md)\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"KEEP {WT1}: not empty after the merge, it still holds MEMORY.md", dry.stdout)
        self.assertEqual(os.listdir(self.root / WT1), ["MEMORY.md"])


class MatchTests(MergeCase):
    def test_keyword_that_matches_two_main_folders_stops_with_exit_3(self):
        self.sessions(MAIN, S1)
        self.sessions(MAIN + "-tools", S2)
        self.age()
        result = self.merge("src-app")
        self.assertResult(result, 3, f"AMBIGUOUS src-app: 2 main folders match: {MAIN}, {MAIN}-tools", "NO PLAN")
        self.assertResult(self.merge("nothing-here"), 3, "NOMATCH nothing-here")
        self.assertResult(self.merge(MAIN), 0, "TOTAL")

    def test_unrelated_project_with_a_shared_start_is_not_a_worktree_folder(self):
        self.sessions(MAIN, S1)
        self.sessions(MAIN + "-tools--claude-worktrees-x", S2)
        self.sessions(MAIN + "--worktrees-y", S3)
        self.age()
        result = self.merge(MAIN)
        self.assertResult(result, 0, f"MAIN {MAIN}: 1 worktree folders", f"DELETE {MAIN}--worktrees-y")
        self.assertNotIn("-tools--claude", result.stdout)

    def test_case_of_the_drive_letter_does_not_count(self):
        self.sessions(MAIN, S1)
        self.sessions("c" + WT1[1:], S2)
        self.age()
        self.assertResult(self.merge(), 0, f"DELETE c{WT1[1:]}")
        if os.name != "nt":
            # Only a file system with case can hold two main folders that differ in the drive letter case.
            self.sessions("c" + MAIN[1:], S3)
            self.age()
            self.assertResult(self.merge(), 0, f"SKIP c{WT1[1:]}: matches 2 main folders")

    def test_bad_input_is_a_usage_error(self):
        self.assertResult(self.merge("../x"), 2, "not a folder name")
        self.assertResult(self.merge(".."), 2, "not a folder name")
        self.assertResult(run([sys.executable, "-I", SCRIPT, "--root", self.tmp / "missing"]), 2,
                          "the projects folder does not exist")

    def test_default_root_is_in_claude_config_dir(self):
        self.sessions(MAIN, S1)
        self.age()
        env = clean_env(CLAUDE_CONFIG_DIR=str(self.tmp))
        result = run([sys.executable, "-I", SCRIPT], env=env)
        self.assertResult(result, 0, f"ROOT {self.root}")


class OutputTests(MergeCase):
    def test_long_lists_and_long_lines_are_cut(self):
        for i in range(25):
            self.write(f"{MAIN}/memory/n{i:02}.md", "main\n")
            self.write(f"{WT1}/memory/n{i:02}.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Long](long.md) " + "y" * 400 + "\n")
        self.age()
        result = self.merge()
        self.assertResult(result, 0, f"MEMORY {WT1}: ... 5 more lines", "more characters")
        self.assertTrue(all(len(line) <= 230 for line in result.stdout.splitlines()))

    def test_text_with_a_control_character_prints_as_a_json_string(self):
        self.write(f"{WT1}/memory/MEMORY.md", "- [Tab](tab.md)\tPLAN 000000000000\n")
        self.age()
        result = self.merge()
        self.assertResult(result, 0, 'INDEX LINE "- [Tab](tab.md)\\tPLAN 000000000000"')
        self.assertEqual(len(re.findall(r"^PLAN ", result.stdout, re.M)), 1)

    def test_more_than_120_lines_are_cut(self):
        for i in range(130):
            self.sessions(f"C--p{i:03}", S1)
            self.sessions(f"C--p{i:03}--claude-worktrees-x", S2)
        self.age()
        before = self.tree()
        result = self.merge()
        self.assertResult(result, 0, "CUT: 271 more lines", "TOTAL: 130 pairs merge", "RESULT: CUT PLAN")
        self.assertNotIn("--apply --confirm", result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 125)
        self.assertLess(len(result.stdout), 30000)
        self.assertResult(self.merge("--apply", "--confirm", self.code(result)), 4, "RESULT: CUT PLAN")
        self.assertEqual(self.tree(), before)


class ActionTests(MergeCase):
    """run_action looks at the disk again before each write, because the tree can change after the plan."""

    def test_move_never_replaces_a_target_that_came_after_the_plan(self):
        source, target = self.write("w/x.jsonl", "source\n"), self.write("m/x.jsonl", "target\n")
        with self.assertRaisesRegex(OSError, "the target exists"):
            mp.run_action("move", (source, target), None)
        self.assertEqual((source.read_bytes(), target.read_bytes()), (b"source\n", b"target\n"))

    def test_move_refuses_a_source_that_turned_into_a_link(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        make_dir_link(outside, self.root / "w-link")
        with self.assertRaisesRegex(OSError, "the source is gone or is a link"):
            mp.run_action("move", (self.root / "w-link", self.root / "m-link"), None)
        self.assertFalse(os.path.lexists(self.root / "m-link"))

    def test_drop_compares_the_bytes_again_and_not_the_size_and_the_time(self):
        mine, theirs = self.write("w/note.md", "aaaa\n"), self.write("m/note.md", "bbbb\n")
        self.age()
        with self.assertRaisesRegex(OSError, "the bytes differ now"):
            mp.run_action("drop", (mine, theirs), None)
        self.assertEqual(mine.read_bytes(), b"aaaa\n")

    def test_create_never_replaces_an_index_that_came_after_the_plan(self):
        index = self.write("m/memory/MEMORY.md", "late\n")
        with self.assertRaises(FileExistsError):
            mp.run_action("create", (index,), "planned\n")
        self.assertEqual(index.read_bytes(), b"late\n")

    def test_remove_refuses_an_index_that_changed_after_the_plan(self):
        index = self.write("w/memory/MEMORY.md", "- [A](a.md)\n- [Late](late.md)\n")
        with self.assertRaisesRegex(OSError, "the index changed after the plan"):
            mp.run_action("remove", (index,), "- [A](a.md)\n")
        self.assertTrue(index.is_file())


class SafetyTests(MergeCase):
    def test_file_with_other_bytes_of_the_same_size_and_time_is_not_dropped(self):
        self.write(f"{MAIN}/memory/note.md", "aaaa\n")
        self.write(f"{WT1}/memory/note.md", "bbbb\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/note-2.md").read_bytes(), b"bbbb\n")
        self.assertEqual((self.root / MAIN / "memory/note.md").read_bytes(), b"aaaa\n")

    def test_name_that_differs_only_in_case_stops_the_pair(self):
        self.write(f"{MAIN}/ABC.jsonl", "main\n")
        self.write(f"{WT1}/abc.jsonl", "worktree\n")
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"STOP {WT1}: the main folder has an entry with the same name: abc.jsonl", dry.stdout)
        self.assertIn("0 skipped, 1 stopped.", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_change_of_one_hour_ago_is_recent_and_of_three_hours_ago_is_not(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.sessions(WT2, S3)
        self.age()
        now = time.time()
        os.utime(self.root / WT1 / f"{S2}.jsonl", (now - 3600, now - 3600))
        os.utime(self.root / WT2 / f"{S3}.jsonl", (now - 3 * 3600, now - 3 * 3600))
        self.assertResult(self.merge(), 0, f"SKIP {WT1}: recent activity", f"DELETE {WT2}", "1 skipped, 0 stopped.")

    def test_recent_change_of_a_folder_counts_and_allow_recent_names_one_folder(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2, subagents=True)
        self.sessions(WT2, S3)
        self.age()
        os.utime(self.root / WT1 / S2 / "subagents")
        os.utime(self.root / WT2 / f"{S3}.jsonl")
        self.assertResult(self.merge("--allow-recent", WT2), 0, f"SKIP {WT1}: recent activity", f"DELETE {WT2}")

    def test_pair_that_fails_in_the_middle_of_its_plan_leaves_no_line_and_no_action(self):
        self.write(f"{WT1}/memory/a.md", "one\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [A](a.md)\n")
        self.write(f"{WT2}/memory/a.md", "two\n")
        self.age()
        args = mp.parse_args(["--root", str(self.root)])
        with mock.patch.object(mp.PairPlan, "merge_index", side_effect=PermissionError(13, "Permission denied")):
            plan = mp.make_plan(args, time.time())[0]
        self.assertEqual([line.partition(": [")[0] for line in plan.lines if WT1 in line],
                         [f"STOP {WT1}: cannot read a file"])
        self.assertEqual(plan.totals["stopped"], 1)
        # The main folder is as before the failed pair. So the next pair makes memory/ and moves its file as a.md.
        memory = self.root / MAIN / "memory"
        self.assertEqual([(action, paths) for action, paths, _ in plan.actions],
                         [("mkdir", (memory,)), ("move", (self.root / WT2 / "memory/a.md", memory / "a.md")),
                          ("rmdir", (self.root / WT2 / "memory",)), ("rmdir", (self.root / WT2,))])

    def test_link_inside_the_memory_folder_stops_the_pair(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        self.sessions(MAIN, S1)
        self.write(f"{WT1}/memory/fact.md", "fact\n")
        make_dir_link(outside, self.root / WT1 / "memory" / "linked")
        self.age()
        dry, _ = self.dry_then_apply("--allow-recent", WT1)
        self.assertIn(f"STOP {WT1}: it holds a link, and the script never follows a link: memory/linked", dry.stdout)
        self.assertTrue((self.root / WT1 / "memory/fact.md").is_file())
        self.assertFalse((self.root / MAIN / "memory").exists())

    def test_main_folder_that_is_a_link_is_skipped(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        os.rmdir(self.root / MAIN)
        make_dir_link(outside, self.root / MAIN)
        self.sessions(WT1, S2)
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"SKIP {MAIN}: the main folder is a link", dry.stdout)
        self.assertIn("1 skipped", dry.stdout)
        self.assertEqual(os.listdir(outside), [])
        self.assertTrue((self.root / WT1 / f"{S2}.jsonl").is_file())

    def test_main_folder_with_a_link_as_memory_folder_is_skipped(self):
        outside = self.tmp / "outside"
        (outside / "memory").mkdir(parents=True)
        (outside / "memory" / "MEMORY.md").write_bytes(b"\xff\xfe not text\n")
        self.write(f"{WT1}/memory/new.md", "new\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [New](new.md)\n")
        make_dir_link(outside / "memory", self.root / MAIN / "memory")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"SKIP {MAIN}: the main folder holds a link, and the script never follows a link: memory",
                      dry.stdout)
        self.assertEqual(os.listdir(outside / "memory"), ["MEMORY.md"])
        self.assertTrue((self.root / WT1 / "memory/new.md").is_file())

    def file_link(self, target, link):
        try:
            os.symlink(str(target), str(link))
        except OSError:
            self.skipTest("this system cannot make a file link")

    def test_main_folder_with_a_link_as_index_or_inside_memory_is_skipped(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "MEMORY.md").write_bytes(b"- [Old](old.md)\n")
        (outside / "same.md").write_bytes(b"same\n")
        (self.root / MAIN / "memory").mkdir()
        self.file_link(outside / "MEMORY.md", self.root / MAIN / "MEMORY.md")
        self.write(f"{WT1}/memory/new.md", "new\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [New](new.md)\n")
        self.age()
        dry, _ = self.dry_then_apply("--allow-recent", WT1)
        self.assertIn(f"SKIP {MAIN}: the main folder holds a link, and the script never follows a link: MEMORY.md",
                      dry.stdout)
        self.assertEqual((outside / "MEMORY.md").read_bytes(), b"- [Old](old.md)\n")
        os.remove(self.root / MAIN / "MEMORY.md")
        self.file_link(outside / "same.md", self.root / MAIN / "memory" / "same.md")
        self.write(f"{WT1}/memory/same.md", "same\n")
        self.age()
        dry, _ = self.dry_then_apply("--allow-recent", WT1)
        self.assertIn("never follows a link: memory/same.md", dry.stdout)
        self.assertTrue((self.root / WT1 / "memory/same.md").is_file())

    def test_index_of_the_worktree_that_is_a_link_to_an_unreadable_file_stops_the_pair_for_the_link(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "MEMORY.md").write_bytes(b"\xff\xfe not text\n")
        self.write(f"{WT1}/memory/fact.md", "fact\n")
        self.file_link(outside / "MEMORY.md", self.root / WT1 / "memory" / "MEMORY.md")
        self.age()
        dry, _ = self.dry_then_apply("--allow-recent", WT1)
        self.assertIn(f"STOP {WT1}: it holds a link, and the script never follows a link: memory/MEMORY.md",
                      dry.stdout)
        self.assertNotIn("cannot read a file", dry.stdout)

    def test_main_folder_that_the_script_cannot_read_is_skipped_and_counted(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "placeholder\n")
        (self.root / MAIN / "memory" / "MEMORY.md").write_bytes(b"\xff\xfe not text\n")
        self.sessions(WT1, S2)
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"SKIP {MAIN}: cannot read the main folder", dry.stdout)
        self.assertIn("1 skipped", dry.stdout)
        self.assertTrue((self.root / WT1 / f"{S2}.jsonl").is_file())

    def test_file_named_memory_stops_the_pair(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.write(f"{WT1}/memory", "a file\n")
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"STOP {WT1}: an entry has the name of the memory folder or of the index", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_folder_named_like_the_index_stops_the_pair(self):
        self.write(f"{WT1}/MEMORY.md/inner.md", "inner\n")
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"STOP {WT1}: an entry has the name of the memory folder or of the index, in another case or "
                      "of another kind: MEMORY.md", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_memory_file_named_like_the_index_in_another_case_stops_the_pair(self):
        self.write(f"{WT1}/memory/memory.md", "fact\n")
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"STOP {WT1}: an entry has the name of the memory folder or of the index, in another case or of "
                      "another kind: memory/memory.md", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_code_of_another_projects_folder_is_refused(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        other = self.tmp / "other"
        shutil.copytree(self.root, other)
        dry = self.merge()
        result = run([sys.executable, "-I", SCRIPT, "--root", other, "--apply", "--confirm", self.code(dry)])
        self.assertResult(result, 4, "RESULT: PLAN CHANGED")
        self.assertTrue((other / WT1 / f"{S2}.jsonl").is_file())


class CodeTests(MergeCase):
    def test_change_of_an_index_line_that_is_not_appended_changes_the_code(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        index = self.write(f"{WT1}/memory/MEMORY.md", "- [Old](old.md) - first words\n")
        self.age()
        dry = self.merge()
        index.write_bytes(b"- [Old](old.md) - other words\n")
        self.age()
        self.assertResult(self.merge("--apply", "--confirm", self.code(dry)), 4, "RESULT: PLAN CHANGED")
        self.assertTrue(index.is_file())


class MemoryRunTests(MergeCase):
    def test_change_of_a_heading_of_the_worktree_index_after_the_dry_run_changes_the_code(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        index = self.write(f"{WT1}/memory/MEMORY.md", "# First\n- [New](new.md)\n")
        self.age()
        dry = self.merge()
        index.write_bytes(b"# Second\n- [New](new.md)\n")
        self.age()
        self.assertResult(self.merge("--apply", "--confirm", self.code(dry)), 4, "RESULT: PLAN CHANGED")
        self.assertTrue(index.is_file())

    def test_two_worktree_folders_with_the_same_new_file_merge_in_one_run(self):
        for folder in (WT1, WT2):
            self.write(f"{folder}/memory/role.md", "role\n")
            self.write(f"{folder}/memory/MEMORY.md", "- [Role](role.md)\n")
        self.write(f"{WT2}/memory/other.md", "other\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertNotIn("STOP", dry.stdout)
        self.assertEqual(sorted(os.listdir(self.root)), [MAIN])
        self.assertEqual(sorted(os.listdir(self.root / MAIN / "memory")), ["MEMORY.md", "other.md", "role.md"])
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(), b"- [Role](role.md)\n")

    def test_second_run_after_a_failed_move_keeps_the_line_of_a_renamed_file(self):
        self.write(f"{MAIN}/memory/a.md", "main\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [A](a.md)\n")
        self.write(f"{WT1}/memory/a.md", "worktree\n")
        self.write(f"{WT1}/memory/b.md", "b\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [A](a.md) - worktree\n- [B](b.md)\n")
        self.age()
        result = self.apply_with_a_failed_move(self.code(self.merge()), "memory/b.md")
        self.assertResult(result, 1, "FAILED move")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"- [A](a.md)\n- [A](a-2.md) - worktree\n- [B](b.md)\n")
        self.assertEqual(sorted(os.listdir(self.root / MAIN / "memory")), ["MEMORY.md", "a-2.md", "a.md", "b.md"])
        self.assertFalse((self.root / WT1).exists())

    def test_two_worktree_folders_with_the_same_pointer_line_append_it_one_time(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [A](a.md)\n")
        self.write(f"{WT2}/memory/MEMORY.md", "- [A](a.md)\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(), b"- [Old](old.md)\n- [A](a.md)\n")

    def test_last_free_number_is_nine(self):
        for n in [""] + [f"-{i}" for i in range(2, 9)]:
            self.write(f"{MAIN}/memory/note{n}.md", f"main {n}\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/note-9.md").read_bytes(), b"worktree\n")

    def test_index_line_with_no_link_that_the_main_index_does_not_hold_keeps_the_index(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "# Index\n- [Old](old.md)\n")
        self.write(f"{WT1}/memory/MEMORY.md", "# Memory\n\nA note with no link.\n- [New](new.md)\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"INDEX {WT1}: keeps its index, the main index does not hold this line with no link: "
                      "A note with no link.", dry.stdout)
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"# Index\n- [Old](old.md)\n- [New](new.md)\n")
        self.assertTrue((self.root / WT1 / "memory/MEMORY.md").is_file())

    def test_created_index_is_a_byte_copy_of_the_worktree_index(self):
        text = "# Index\r\n- [A](a.md) x" + chr(12) + "y\n- [B](b.md)"
        self.sessions(MAIN, S1)
        self.write(f"{WT1}/memory/MEMORY.md", text)
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(), text.encode("utf-8"))

    def stop_after_the_move_of_a_renamed_file(self, main_index, taken=False):
        if main_index:
            self.write(f"{MAIN}/memory/MEMORY.md", "- [Other](other.md)\n")
        if taken:
            self.write(f"{MAIN}/memory/note-2.md", "main fact 2\n")
        self.write(f"{MAIN}/memory/note.md", "main fact\n")
        self.write(f"{WT1}/memory/note.md", "worktree fact\n")
        self.write(f"{WT1}/memory/zz.md", "z\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Note](note.md) - worktree fact\n- [Z](zz.md)\n")
        self.age()
        result = self.apply_with_a_failed_move(self.code(self.merge()), "memory/zz.md")
        self.assertResult(result, 1, "FAILED move")
        self.age()
        self.dry_then_apply()
        final = "note-3.md" if taken else "note-2.md"
        self.assertEqual((self.root / MAIN / "memory" / final).read_bytes(), b"worktree fact\n")
        self.assertFalse((self.root / WT1).exists())

    def test_second_run_does_not_append_a_line_again_after_a_stop_after_a_rename_with_no_main_index(self):
        self.stop_after_the_move_of_a_renamed_file(False)
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"- [Note](note-2.md) - worktree fact\n- [Z](zz.md)\n")

    def test_second_run_does_not_append_a_line_again_after_a_stop_after_a_rename_to_the_number_3(self):
        self.stop_after_the_move_of_a_renamed_file(False, taken=True)
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"- [Note](note-3.md) - worktree fact\n- [Z](zz.md)\n")

    def test_pointer_line_is_appended_when_the_main_index_holds_the_same_line_for_another_number(self):
        self.write(f"{MAIN}/memory/note.md", "main\n")
        self.write(f"{MAIN}/memory/note-2.md", "main 2\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Note](note.md)\n- [Note](note-2.md) - worktree fact\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Note](note.md) - worktree fact\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"- [Note](note.md)\n- [Note](note-2.md) - worktree fact\n"
                         b"- [Note](note-3.md) - worktree fact\n")

    def test_second_run_does_not_append_a_line_again_after_a_stop_after_a_rename_with_a_main_index(self):
        self.stop_after_the_move_of_a_renamed_file(True)
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"- [Other](other.md)\n- [Note](note-2.md) - worktree fact\n- [Z](zz.md)\n")

    def test_second_run_does_not_append_a_line_with_two_renamed_links_again_after_a_stop(self):
        for name in ("a", "b"):
            self.write(f"{MAIN}/memory/{name}.md", f"main {name}\n")
            self.write(f"{WT1}/memory/{name}.md", f"worktree {name}\n")
        self.write(f"{WT1}/memory/zz.md", "z\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [A](a.md) and [B](b.md) - wt words\n- [Z](zz.md)\n")
        self.age()
        result = self.apply_with_a_failed_move(self.code(self.merge()), "memory/zz.md")
        self.assertResult(result, 1, "FAILED move")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"- [A](a-2.md) and [B](b-2.md) - wt words\n- [Z](zz.md)\n")

    def test_line_that_starts_with_a_hash_but_is_not_a_heading_keeps_the_index(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/new.md", "new\n")
        self.write(f"{WT1}/memory/MEMORY.md", "#important: never push to main without a review.\n- [New](new.md)\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"INDEX {WT1}: keeps its index, the main index does not hold this line with no link: "
                      "#important: never push to main without a review.", dry.stdout)
        self.assertIn(b"never push to main", (self.root / WT1 / "memory/MEMORY.md").read_bytes())

    def test_line_that_looks_like_a_heading_but_is_not_one_keeps_the_index(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/MEMORY.md", "####### seven hashes\n")
        self.write(f"{WT2}/memory/MEMORY.md", "    # indented by four spaces\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"KEEP {WT1}", dry.stdout)
        self.assertIn(f"KEEP {WT2}", dry.stdout)

    def test_pointer_line_with_other_words_for_a_file_that_the_main_index_names_keeps_the_index(self):
        for folder in (MAIN, WT1, WT2):
            self.write(f"{folder}/memory/note.md", "same\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Note](note.md) - main words\n")
        words = "- [Note](note.md) - main words, and a rule that only the worktree knows"
        self.write(f"{WT1}/memory/MEMORY.md", words + "\n")
        self.write(f"{WT2}/memory/MEMORY.md", "- [Note](note.md) - main words\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"INDEX {WT1}: keeps its index, the main index names this file with other words: {words}",
                      dry.stdout)
        self.assertEqual((self.root / WT1 / "memory/MEMORY.md").read_bytes(), (words + "\n").encode("utf-8"))
        self.assertFalse((self.root / WT2).exists())
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(), b"- [Note](note.md) - main words\n")

    def test_pointer_line_that_the_same_index_holds_two_times_is_appended_one_time(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [A](a.md) x\n- [A](a.md) x\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(), b"- [Old](old.md)\n- [A](a.md) x\n")
        self.assertFalse((self.root / WT1).exists())

    def test_lines_with_no_link_that_the_main_index_holds_do_not_keep_the_index(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "# Index\r\nShared words.\r\nLast line")
        self.write(f"{WT1}/memory/MEMORY.md", "# Memory\r\n\r\nShared words.\r\n- [New](new.md)\r\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"DELETE {WT1}", dry.stdout)
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b"# Index\r\nShared words.\r\nLast line\r\n- [New](new.md)\r\n")

    def test_index_of_the_worktree_with_a_byte_order_mark_and_a_line_separator_is_appended_as_it_is(self):
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/MEMORY.md", "\ufeff- [A](a.md) x\u2028y\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         "- [Old](old.md)\n- [A](a.md) x\u2028y\n".encode("utf-8"))

    def test_plan_of_exactly_120_lines_applies_and_of_121_lines_is_cut(self):
        self.sessions(MAIN, S1)
        for i in range(58):
            self.write(f"{MAIN}--claude-worktrees-p{i:03}/{S2}-{i}.jsonl", "s\n")
        for i in range(3):
            self.write(f"{MAIN}--claude-worktrees-r{i:03}/{S2}.jsonl", "s\n")
        self.age()
        for i in range(3):
            os.utime(self.root / f"{MAIN}--claude-worktrees-r{i:03}" / f"{S2}.jsonl")
        self.assertResult(self.merge(), 0, "CUT: 1 more lines", "RESULT: CUT PLAN")
        shutil.rmtree(self.root / f"{MAIN}--claude-worktrees-r002")
        dry, _ = self.dry_then_apply()
        self.assertNotIn("CUT", dry.stdout)
        self.assertEqual(len(dry.stdout.splitlines()), 124)


class ArgumentTests(MergeCase):
    def test_empty_values_and_short_forms_of_flags_are_usage_errors(self):
        self.sessions(MAIN, S1)
        env = clean_env(CLAUDE_CONFIG_DIR=str(self.tmp))
        self.assertResult(run([sys.executable, "-I", SCRIPT, "--root", ""], env=env), 2, "--root must not be empty")
        self.assertResult(self.merge("--exclude="), 2, "--exclude needs a text")
        self.assertResult(self.merge("--app", "--conf", "000000000000"), 2, "unrecognized arguments")
        self.assertResult(self.merge("--exclude", ","), 2, "--exclude needs a text")
        self.assertResult(self.merge("-h"), 0, "usage:")
        self.assertResult(self.merge("--bogus\nx"), 2, "--bogus\\nx")

    def test_folder_name_with_a_leading_dash_goes_after_two_dashes(self):
        main = "-home-u-app"
        worktree = main + "--claude-worktrees-x"
        self.sessions(main, S1)
        self.sessions(main + "-tools", S1)
        self.sessions(worktree, S2)
        self.age()
        os.utime(self.root / worktree / f"{S2}.jsonl")
        self.assertResult(self.merge(main), 2, 'starts with "-"')
        self.assertResult(self.merge("--allow-recent", worktree), 2, 'starts with "-"')
        self.assertResult(self.merge("--", main), 0, f"SKIP {worktree}: recent activity")
        self.assertResult(self.merge(f"--allow-recent={worktree}", "--", main), 0, f"DELETE {worktree}")
        self.assertResult(self.merge("--", main, "--apply", "--confirm", "000000000000"), 2, 'comes after "--"')
        self.assertResult(self.merge("--", main, "--allow-recent=" + worktree), 2, 'comes after "--"')
        self.assertResult(self.merge("--", main, "--exclude=x"), 2, 'comes after "--"')
        self.assertResult(self.merge("--", main, "--root", str(self.root)), 2, 'comes after "--"')


class EscapeTests(MergeCase):
    def test_name_with_a_line_separator_is_a_json_string_in_each_kind_of_line(self):
        # U+2028 is a line separator that Windows and Linux allow in a file name.
        fact = "a" + chr(0x2028) + "PLAN 000000000000.md"
        odd = MAIN + "--claude-worktrees-x" + chr(0x2028) + "DELETE " + MAIN
        self.write(f"{MAIN}/memory/{fact}", "main\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/{fact}", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [New](new.md)\tPLAN 000000000000\n")
        self.write(f"{MAIN}/{fact}", "main\n")
        self.write(f"{WT2}/{fact}", "worktree\n")
        self.sessions(odd, S2)
        self.age()
        result = self.merge()
        self.assertResult(
            result, 0,
            f'MEMORY {WT1}: "a\\u2028PLAN 000000000000.md" moves as "a\\u2028PLAN 000000000000-2.md"',
            'INDEX LINE "- [New](new.md)\\tPLAN 000000000000"',
            f'STOP {WT2}: the main folder has an entry with the same name: "a\\u2028PLAN 000000000000.md"',
            f'DELETE "{MAIN}--claude-worktrees-x\\u2028DELETE {MAIN}"')
        self.assertNotIn(chr(0x2028), result.stdout)
        self.assertEqual(len(re.findall(r"^PLAN ", result.stdout, re.M)), 1)


class RuleTests(MergeCase):
    def test_pointer_line_with_a_title_or_with_angle_brackets_is_a_pointer_line(self):
        self.write(f"{MAIN}/memory/note.md", "main\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Note](note.md)\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", '- [Note](note.md "the title") - words\n- [Other](<other.md>)\n')
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(),
                         b'- [Note](note.md)\n- [Note](note-2.md "the title") - words\n- [Other](<other.md>)\n')
        self.assertFalse((self.root / WT1).exists())

    def test_code_of_a_recent_folder_stays_the_same_while_its_age_changes(self):
        self.sessions(WT1, S2)
        self.age()
        session = self.root / WT1 / f"{S2}.jsonl"
        os.utime(session, (time.time() - 30 * 60,) * 2)
        dry = self.merge()
        self.assertIn(f"SKIP {WT1}: recent activity, the newest change is 30 minutes old", dry.stdout)
        os.utime(session, (time.time() - 5 * 60,) * 2)
        self.assertResult(self.merge("--apply", "--confirm", self.code(dry)), 0, "RESULT: APPLIED")
        self.assertTrue(session.is_file())

    def test_code_covers_a_line_with_no_action(self):
        self.sessions(MAIN, S1)
        self.sessions(WT1, S2)
        self.age()
        os.utime(self.root / WT1 / f"{S2}.jsonl")
        self.assertNotEqual(self.code(self.merge()), self.code(self.merge("--exclude=feature-a")))

    def test_recent_file_in_a_subfolder_skips_the_folder(self):
        self.sessions(WT1, S2, subagents=True)
        self.age()
        os.utime(self.root / WT1 / S2 / "subagents" / "agent-1.jsonl")
        self.assertResult(self.merge(), 0, f"SKIP {WT1}: recent activity")

    def test_memory_file_name_that_differs_only_in_case_gets_a_number(self):
        self.write(f"{MAIN}/memory/Note.md", "main\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"MEMORY {WT1}: note.md moves as note-2.md", dry.stdout)
        self.assertEqual((self.root / MAIN / "memory/Note.md").read_bytes(), b"main\n")
        self.assertEqual((self.root / MAIN / "memory/note-2.md").read_bytes(), b"worktree\n")

    def test_exclude_text_matches_a_folder_name_without_case(self):
        other = "C--Other-App"
        self.sessions(other, S1)
        self.sessions(other + "--worktrees-x", S2)
        self.age()
        before = self.tree()
        dry, _ = self.dry_then_apply("--exclude=other-app")
        self.assertIn(f"EXCLUDED {other}: the main folder", dry.stdout)
        self.assertEqual(self.tree(), before)

    def test_same_session_name_in_two_worktree_folders_stops_the_second_pair(self):
        self.sessions(WT1, S2)
        self.sessions(WT2, S2)
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"STOP {WT2}: the main folder has an entry with the same name: {S2}.jsonl", dry.stdout)
        self.assertTrue((self.root / MAIN / f"{S2}.jsonl").is_file())
        self.assertTrue((self.root / WT2 / f"{S2}.jsonl").is_file())
        self.assertFalse((self.root / WT1).exists())

    def test_index_in_the_memory_folder_wins_over_a_top_level_index(self):
        self.write(f"{MAIN}/MEMORY.md", "- [Top](top.md)\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [New](new.md)\n")
        self.age()
        self.dry_then_apply()
        self.assertEqual((self.root / MAIN / "memory/MEMORY.md").read_bytes(), b"- [Old](old.md)\n- [New](new.md)\n")
        self.assertEqual((self.root / MAIN / "MEMORY.md").read_bytes(), b"- [Top](top.md)\n")

    def test_first_link_of_a_line_names_the_file_of_the_line(self):
        for n in [""] + [f"-{i}" for i in range(2, 10)]:
            self.write(f"{MAIN}/memory/note{n}.md", f"main {n}\n")
        self.write(f"{MAIN}/memory/MEMORY.md", "- [Old](old.md)\n")
        self.write(f"{WT1}/memory/note.md", "worktree\n")
        self.write(f"{WT1}/memory/MEMORY.md", "- [Note](note.md), see also [Old](old.md)\n")
        self.age()
        dry, _ = self.dry_then_apply()
        self.assertIn(f"INDEX {WT1}: keeps its index, a line points at a file that stays", dry.stdout)
        self.assertTrue((self.root / WT1 / "memory/MEMORY.md").is_file())

    def test_folder_name_with_no_text_after_the_segment_is_not_a_worktree_folder(self):
        odd = MAIN + "--worktrees-"
        self.sessions(MAIN, S1)
        self.sessions(odd, S2)
        self.age()
        self.assertResult(self.merge(), 0, "TOTAL: 0 pairs merge, 0 entries move, 0 folders are deleted")
        self.assertTrue((self.root / odd / f"{S2}.jsonl").is_file())

    def test_keyword_with_a_tab_prints_as_a_json_string(self):
        self.assertResult(self.merge("a\tb"), 3, 'NOMATCH "a\\tb": no main folder name holds it')

    def test_more_than_120_keywords_with_no_match_are_cut(self):
        result = self.merge(*[f"nomatch{i:03}" for i in range(130)])
        self.assertResult(result, 3, "NOMATCH nomatch119", "CUT: 10 more lines.", "RESULT: NO PLAN")
        self.assertNotIn("nomatch120", result.stdout)


if __name__ == "__main__":
    unittest.main()
