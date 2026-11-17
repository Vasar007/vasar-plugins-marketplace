"""Tests for essentials/dev-essentials/scripts/merge_projects.py.

Each test builds a projects folder in a temporary folder and runs the script as a child process, as the
command merge-worktree-projects does. The files get a modification time of 3 days ago, so that the check
for recent activity passes, unless a test wants a recent file.
"""
import os
import re
import sys
import time
import unittest
from pathlib import Path

from support import REPO
from testkit import ScratchCase, clean_env, run

SCRIPT = REPO / "essentials/dev-essentials/scripts/merge_projects.py"
MAIN = "C--src-app"
WT1 = MAIN + "--claude-worktrees-feature-a"
WT2 = MAIN + "--claude-worktrees-feature-b"
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
        applied = self.merge(*args, "--apply", "--confirm", self.code(dry))
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
        return run([sys.executable, "-I", "-c", FAIL_RENAME, name, SCRIPT, "--root", self.root,
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
        self.assertIn(f"EXCLUDED {WT1}", dry.stdout)
        self.assertNotIn("STOP", dry.stdout)
        self.assertTrue((self.root / WT1 / f"{S1}.jsonl").is_file())
        self.assertFalse((self.root / WT2).exists())

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
        self.assertTrue(all(len(line) <= 330 for line in result.stdout.splitlines()))

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
        result = self.merge()
        self.assertResult(result, 0, "CUT: ", "TOTAL: 130 pairs merge")
        self.assertLess(len(result.stdout), 30000)


if __name__ == "__main__":
    unittest.main()
