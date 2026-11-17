"""Tests for skills/trim-artifacts/scripts/trim_report.py.

Each test builds a before tree and an after tree in a temporary folder and runs
the script as a child process, as the skill does.
"""
import os
import sys
import unittest

from support import REPO
from testkit import ScratchCase, run

SCRIPT = REPO / "essentials/dev-essentials/skills/trim-artifacts/scripts/trim_report.py"
DECISION = r"(?m)^## Decision \d+\n\nQuote: .*\nDecision: .*$"
NOTES = "# Notes\n\nREQ-1 and REQ-2 are open.\n\n## Decision 1\n\nQuote: keep it\nDecision: keep the cache\n"


class TrimReportCase(ScratchCase):
    def setUp(self):
        super().setUp()
        self.before = self.tmp / "before"
        self.after = self.tmp / "after"

    def tree(self, root, files):
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def run_trim(self, before, after, *args):
        self.tree(self.before, before)
        self.tree(self.after, after)
        return self.run_script("--before", self.before, "--after", self.after, *args)

    def run_script(self, *args):
        return run([sys.executable, "-I", SCRIPT, *args])


class SizeTableTests(TrimReportCase):
    def test_statuses(self):
        before = {"kept.md": "same\n", "crlf.md": "a\nb\n", "cut.md": "x" * 100 + "\n",
                  "gone.md": "old\n", "grow.md": "a\n"}
        after = {"kept.md": "same\n", "crlf.md": "a\r\nb\r\n", "cut.md": "x" * 70 + "\n",
                 "new.md": "fresh\n", "grow.md": "a\nb\n"}
        result = self.run_trim(before, after, "--target-percent", "60")
        self.assertResult(result, 0, "RESULT: PASS",
                          "| kept.md | 5 | 5 | 100 | 1 | 1 | kept (above 60%) |",
                          "| crlf.md | 4 | 6 | 150 | 2 | 2 | line endings only (above 60%) |",
                          "| cut.md | 101 | 71 | 70 | 1 | 1 | trimmed (above 60%) |",
                          "| gone.md | 4 | 0 | 0 | 1 | 0 | deleted |",
                          "| new.md | 0 | 6 | - | 0 | 1 | new |",
                          "grown (above 60%)",
                          "| **Total** |")

    def test_glob_limits_the_files(self):
        before = {"top.md": "a\n", "sub/deep.md": "b\n", "skip.txt": "c\n"}
        result = self.run_trim(before, before, "--glob", "*.md")
        self.assertResult(result, 0, "| top.md |")
        self.assertNotIn("deep.md", result.stdout)
        self.assertNotIn("skip.txt", result.stdout)


class IdTests(TrimReportCase):
    def test_lost_id_fails(self):
        result = self.run_trim({"n.md": NOTES}, {"n.md": NOTES.replace("REQ-2", "REQ-3")},
                               "--id-regex", r"\bREQ-\d+\b")
        self.assertResult(result, 1, "2 before, 2 after", "- Missing: REQ-2", "- New: REQ-3", "RESULT: FAIL")

    def test_kept_ids_pass(self):
        result = self.run_trim({"n.md": NOTES}, {"n.md": NOTES.replace("are open", "stay open")},
                               "--id-regex", r"\bREQ-\d+\b")
        self.assertResult(result, 0, "- Missing: none", "RESULT: PASS")

    def test_regex_that_matches_nothing_fails(self):
        result = self.run_trim({"n.md": NOTES}, {"n.md": NOTES}, "--id-regex", r"\bTASK-\d+\b")
        self.assertResult(result, 1, "FAIL: regex matched nothing in the before tree")


class ProtectedBlockTests(TrimReportCase):
    def check(self, after, *extra, before=None):
        return self.run_trim(before or {"n.md": NOTES}, after, "--protected-regex", DECISION, *extra)

    def test_unchanged_block_passes(self):
        result = self.check({"n.md": NOTES.replace("REQ-1 and REQ-2 are open.\n\n", "")})
        self.assertResult(result, 0, "1 blocks checked, 0 missing or changed")

    def test_block_with_crlf_still_matches(self):
        result = self.check({"n.md": NOTES.replace("\n", "\r\n")})
        self.assertResult(result, 0, "1 blocks checked, 0 missing or changed")

    def test_changed_block_fails(self):
        result = self.check({"n.md": NOTES.replace("keep the cache", "drop the cache")})
        self.assertResult(result, 1, "- CHANGED n.md:5: ## Decision 1", "RESULT: FAIL")

    def test_missing_block_fails(self):
        result = self.check({"n.md": "# Notes\n"})
        self.assertResult(result, 1, "- MISSING n.md:5: ## Decision 1")

    def test_block_moved_to_another_file_passes(self):
        block = NOTES[NOTES.index("## Decision 1"):]
        result = self.check({"n.md": "# Notes\n", "decisions.md": block})
        self.assertResult(result, 0, "- IN OTHER FILE (intact, moved or deduplicated) n.md:5")

    def test_allowed_block_with_tombstone_passes(self):
        result = self.check({"n.md": "# Notes\n\n## Decision 1 (withdrawn)\n"},
                            "--allow-changed", r"^n\.md:## Decision 1\b")
        self.assertResult(result, 0, "- ALLOWED n.md:5: ## Decision 1", "1 allowed")

    def test_allowed_block_without_tombstone_fails(self):
        result = self.check({"n.md": "# Notes\n"}, "--allow-changed", r"^n\.md:## Decision 1\b")
        self.assertResult(result, 1, "- WITHDRAWN, NO TOMBSTONE n.md:5")

    def test_allow_regex_for_another_file_does_not_apply(self):
        result = self.check({"n.md": "# Notes\n\n## Decision 1 (withdrawn)\n"},
                            "--allow-changed", r"^other\.md:## Decision 1\b")
        self.assertResult(result, 1, "- CHANGED n.md:5")

    def test_regex_that_matches_nothing_fails(self):
        result = self.run_trim({"n.md": "# Notes\n"}, {"n.md": "# Notes\n"}, "--protected-regex", DECISION)
        self.assertResult(result, 1, "FAIL: regex matched nothing in the before tree")

    def test_invalid_utf8_in_a_block_does_not_crash(self):
        before = {"n.md": NOTES.encode("utf-8").replace(b"keep the cache", b"keep \xff cache")}
        result = self.check({"n.md": b"# Notes\n"}, before=before)
        self.assertResult(result, 1, "- MISSING n.md:5")
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_in_a_printed_line_is_escaped(self):
        before = {"n.md": b"# Notes\n\nQuote: keep \xff it\n"}
        result = self.run_trim(before, {"n.md": b"# Notes\n"}, "--protected-regex", r"(?m)^Quote: .*$")
        self.assertResult(result, 1, r"- MISSING n.md:3: Quote: keep \udcff it")
        self.assertNotIn("Traceback", result.stderr)


class DanglingReferenceTests(TrimReportCase):
    def test_reference_to_deleted_file_fails(self):
        result = self.run_trim({"a.md": "See OLD.md.\n", "old.md": "x\n"}, {"a.md": "See OLD.md.\n"})
        self.assertResult(result, 1, "- old.md: DANGLING in a.md:1")

    def test_similar_names_are_not_references(self):
        text = "See my-old.md, old.md.bak, and old.mdx.\n"
        result = self.run_trim({"a.md": text, "old.md": "x\n"}, {"a.md": text})
        self.assertResult(result, 0, "- old.md: no references")

    def test_same_name_in_another_folder_is_ambiguous(self):
        before = {"a.md": "See notes.md.\n", "x/notes.md": "1\n", "y/notes.md": "2\n"}
        after = {"a.md": "See notes.md.\n", "y/notes.md": "2\n"}
        result = self.run_trim(before, after)
        self.assertResult(result, 0, "- x/notes.md: AMBIGUOUS", "RESULT: PASS")


class UsageErrorTests(TrimReportCase):
    def test_missing_directory(self):
        self.before.mkdir()
        result = self.run_script("--before", self.before, "--after", self.tmp / "nope")
        self.assertResult(result, 2, "--after is not a directory")

    def test_trees_that_contain_each_other(self):
        self.tree(self.before, {"n.md": NOTES})
        inner = self.before / "copy"
        inner.mkdir()
        for after in (self.before, inner):
            with self.subTest(after=after):
                result = self.run_script("--before", self.before, "--after", after)
                self.assertResult(result, 2, "must not contain each other")

    def test_symbolic_link_to_the_same_tree(self):
        self.tree(self.before, {"n.md": NOTES})
        link = self.tmp / "link"
        try:
            os.symlink(self.before, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"cannot create a symbolic link here: {exc}")
        self.assertResult(self.run_script("--before", self.before, "--after", link), 2, "must not contain")

    def test_bad_regex(self):
        result = self.run_trim({"n.md": NOTES}, {"n.md": NOTES}, "--id-regex", "(")
        self.assertResult(result, 2, "bad regex")

    def test_no_file_matches(self):
        result = self.run_trim({"n.txt": "x"}, {"n.txt": "x"})
        self.assertResult(result, 2, "no files match")

    def test_absolute_glob(self):
        result = self.run_trim({"n.md": NOTES}, {"n.md": NOTES}, "--glob", str(self.tmp / "*.md"))
        self.assertResult(result, 2, "cannot read")

    def test_unknown_flag(self):
        self.assertEqual(self.run_script("--nope").returncode, 2)


# Runs the script, with an open() for writing that fails for one file name: python -I -c FAIL_WRITE <name> <script> <args>.
FAIL_WRITE = (
    "import builtins, os, runpy, sys\n"
    "real, name = builtins.open, sys.argv[1]\n"
    "def failing(file, mode='r', *args, **kwargs):\n"
    "    if os.path.basename(str(file)) == name and ('w' in mode or 'x' in mode):\n"
    "        raise PermissionError(13, 'the disk refuses the write', str(file))\n"
    "    return real(file, mode, *args, **kwargs)\n"
    "builtins.open = failing\n"
    "sys.argv = sys.argv[2:]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)
# Runs the script, with an open() for writing that first writes the file for one name, as another process would.
APPEAR_ON_WRITE = (
    "import builtins, os, runpy, sys\n"
    "real, name = builtins.open, sys.argv[1]\n"
    "def appearing(file, mode='r', *args, **kwargs):\n"
    "    if os.path.basename(str(file)) == name and ('w' in mode or 'x' in mode):\n"
    "        with real(file, 'wb') as other:\n"
    "            other.write(b'written by another process\\n')\n"
    "    return real(file, mode, *args, **kwargs)\n"
    "builtins.open = appearing\n"
    "sys.argv = sys.argv[2:]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)
TRIMMED = NOTES.replace("REQ-1 and REQ-2 are open.\n\n", "REQ-1, REQ-2 open.\n\n")
REFUSED = "RESULT: REFUSED. No file was changed."


def make_dir_link(target, link):
    """A link to a folder: a symbolic link on Linux, a junction on Windows (no admin right needed)."""
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(str(target), str(link))


class ApplyCase(TrimReportCase):
    """A workspace, its backup, and the orig and target copies of one batch. The plan changes notes/a.md, deletes
    notes/log/old.md, and adds notes/new.md. notes/keep.md stays."""

    START = {"notes/a.md": NOTES, "notes/keep.md": "Keep REQ-3.\n", "notes/log/old.md": "Old session log.\n",
             "notes/log/raw.txt": "not a glob file\n"}

    def setUp(self):
        super().setUp()
        self.orig, self.target = self.tmp / "scratch" / "orig", self.tmp / "scratch" / "target"
        start = {k: v for k, v in self.START.items() if k.endswith(".md")}
        self.tree(self.after, self.START)
        self.tree(self.before, self.START)
        self.tree(self.orig, start)
        plan = dict(start, **{"notes/a.md": TRIMMED, "notes/new.md": "Moved REQ-1 note.\n"})
        del plan["notes/log/old.md"]
        self.tree(self.target, plan)

    def apply(self, *extra, prefix=(), delete=("notes/log/old.md",)):
        flags = [part for path in delete for part in ("--delete", path)]
        return run([sys.executable, "-I", *prefix, SCRIPT, "apply", "--orig", self.orig, "--target", self.target,
                    "--before", self.before, "--after", self.after, "--id-regex", r"\bREQ-\d+\b",
                    "--protected-regex", DECISION, *flags, *extra])

    def snapshot(self):
        return {p.relative_to(self.after).as_posix(): (p.read_bytes() if p.is_file() else None)
                for p in sorted(self.after.rglob("*"))}

    def assertRefused(self, result, *texts):
        self.assertResult(result, 3, REFUSED, *texts)
        self.assertTrue(result.stdout.rstrip().endswith(REFUSED), result.stdout)


class ApplyTests(ApplyCase):
    def test_apply_writes_the_plan_and_passes_the_checks(self):
        result = self.apply()
        self.assertResult(result, 0, "PLAN CHECK: PASS (--orig against --target)",
                          "APPLIED: 1 changed, 1 new, 1 deleted, 0 folders removed, 0 done before.",
                          "CHANGED notes/a.md", "NEW notes/new.md", "DELETED notes/log/old.md", "- Missing: none", "1 blocks checked, 0 missing or changed",
                          "| notes/a.md |", "RESULT: PASS")
        self.assertEqual((self.after / "notes/a.md").read_bytes(), TRIMMED.encode("utf-8"))
        self.assertEqual((self.after / "notes/new.md").read_bytes(), b"Moved REQ-1 note.\n")
        self.assertFalse((self.after / "notes/log/old.md").exists())
        self.assertEqual(sorted(p.name for p in (self.after / "notes").iterdir()), ["a.md", "keep.md", "log", "new.md"])
        self.assertEqual((self.after / "notes/log/raw.txt").read_bytes(), b"not a glob file\n")
        self.assertTrue(result.stdout.rstrip().endswith("RESULT: PASS"))

    def test_emptied_folders_go_up_to_the_workspace_and_other_folders_stay(self):
        (self.after / "notes/log/raw.txt").unlink()
        (self.after / "empty").mkdir()
        result = self.apply()
        self.assertResult(result, 0, "REMOVED FOLDER notes/log", "1 folders removed")
        self.assertFalse((self.after / "notes/log").exists())
        self.assertTrue((self.after / "notes").is_dir())
        self.assertTrue((self.after / "empty").is_dir())
        self.assertTrue(self.after.is_dir())

    def test_the_removal_stops_at_the_workspace_root(self):
        roots = [self.tmp / name for name in ("ws2", "backup2", "orig2", "target2")]
        for root in roots[:3]:
            self.tree(root, {"only/gone.md": "x\n"})
        roots[3].mkdir()
        result = run([sys.executable, "-I", SCRIPT, "apply", "--after", roots[0], "--before", roots[1],
                      "--orig", roots[2], "--target", roots[3], "--delete", "only/gone.md"])
        self.assertResult(result, 0, "DELETED only/gone.md", "REMOVED FOLDER only", "RESULT: PASS")
        self.assertEqual(list(roots[0].iterdir()), [])

    def test_a_second_run_finds_each_file_done(self):
        self.assertEqual(self.apply().returncode, 0)
        result = self.apply()
        self.assertResult(result, 0, "APPLIED: 0 changed, 0 new, 0 deleted, 0 folders removed, 3 done before.",
                          "DONE BEFORE notes/a.md", "DONE BEFORE notes/log/old.md", "DONE BEFORE notes/new.md")

    def test_a_file_that_the_plan_keeps_is_not_tested_or_written(self):
        # Another batch already trimmed keep.md, so it differs from orig. This batch must leave it alone.
        (self.after / "notes/keep.md").write_bytes(b"Keep REQ-3 (trimmed).\n")
        result = self.apply("--delete", "notes/keep.md")
        self.assertResult(result, 0, "RESULT: PASS")
        self.assertEqual((self.after / "notes/keep.md").read_bytes(), b"Keep REQ-3 (trimmed).\n")

    def test_a_windows_path_in_delete_is_the_same_path(self):
        self.assertResult(self.apply(delete=("notes\\log\\old.md",)), 0, "DELETED notes/log/old.md")

    def test_a_failed_check_after_the_apply_exits_1(self):
        # The plan passes its own checks, but another batch lost REQ-3 in the workspace.
        (self.after / "notes/keep.md").write_bytes(b"Keep it.\n")
        result = self.apply()
        self.assertResult(result, 1, "CHANGED notes/a.md", "- Missing: REQ-3", "RESULT: FAIL")
        self.assertTrue(result.stdout.rstrip().endswith("RESULT: FAIL"))


class ApplyRefusalTests(ApplyCase):
    def check_refused(self, *texts, delete=("notes/log/old.md",), extra=()):
        before = self.snapshot()
        result = self.apply(*extra, delete=delete)
        self.assertRefused(result, *texts)
        self.assertEqual(self.snapshot(), before, "a refused run changed the workspace")
        return result

    def test_a_workspace_file_that_changed_after_the_plan(self):
        (self.after / "notes/a.md").write_bytes(b"An edit of the user.\n")
        self.check_refused("REFUSED notes/a.md: it differs from --orig and from --target. Restore it from the backup")

    def test_a_workspace_file_that_is_missing(self):
        (self.after / "notes/a.md").unlink()
        self.check_refused("REFUSED notes/a.md: it is missing in --after.")

    def test_a_new_file_that_exists_is_not_overwritten(self):
        (self.after / "notes/new.md").write_bytes(b"A file of the user.\n")
        self.check_refused("REFUSED notes/new.md: it exists in --after already.")

    def test_a_deletion_with_no_approval(self):
        self.check_refused("REFUSED notes/log/old.md: the plan deletes it, but no --delete flag approves it.",
                           delete=())

    def test_a_backup_that_differs_or_is_missing(self):
        (self.before / "notes/a.md").write_bytes(b"older\n")
        (self.before / "notes/log/old.md").unlink()
        self.check_refused("REFUSED notes/a.md: the backup copy is missing or differs from --orig.",
                           "REFUSED notes/log/old.md: the backup copy is missing or differs from --orig.")

    def test_a_plan_that_fails_its_own_checks(self):
        (self.target / "notes/a.md").write_bytes(TRIMMED.replace("REQ-2", "REQ-X").encode("utf-8"))
        self.check_refused("REFUSED: the plan fails its checks on --orig against --target", "- Missing: REQ-2")

    def test_a_link_on_the_path(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "a.md").write_bytes(NOTES.encode("utf-8"))
        for name in ("a.md", "keep.md"):
            (self.after / "notes" / name).unlink()
        (self.after / "notes").rename(self.tmp / "real-notes")
        try:
            make_dir_link(outside, self.after / "notes")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"cannot create a folder link here: {exc}")
        self.check_refused("REFUSED notes/a.md: a link is on its path in --after.")
        self.assertEqual((outside / "a.md").read_bytes(), NOTES.encode("utf-8"))

    def test_a_folder_where_the_plan_has_a_file(self):
        (self.after / "notes/new.md").mkdir()
        self.check_refused("REFUSED notes/new.md: it is not a regular file in --after.")

    def test_one_refusal_stops_every_write(self):
        (self.after / "notes/new.md").write_bytes(b"A file of the user.\n")
        self.check_refused("REFUSED notes/new.md")
        self.assertEqual((self.after / "notes/a.md").read_bytes(), NOTES.encode("utf-8"))
        self.assertTrue((self.after / "notes/log/old.md").exists())


class ApplyUsageTests(ApplyCase):
    def test_bad_delete_paths(self):
        for path, text in (("/notes/a.md", "--delete needs a path relative to --after"),
                           ("../a.md", "--delete needs a path relative to --after"),
                           ("", "--delete needs a path relative to --after"),
                           ("notes/none.md", "--delete names no file of --orig: notes/none.md")):
            with self.subTest(path=path):
                self.assertResult(self.apply(delete=(path,)), 2, text)

    def test_trees_that_contain_each_other(self):
        inside = self.after / "scratch-orig"
        inside.mkdir()
        self.tree(inside, {"notes/a.md": NOTES})
        result = run([sys.executable, "-I", SCRIPT, "apply", "--orig", inside, "--target", self.target,
                      "--before", self.before, "--after", self.after])
        self.assertResult(result, 2, "the after tree and the orig tree must not contain each other")
        result = run([sys.executable, "-I", SCRIPT, "apply", "--orig", self.orig, "--target", self.orig,
                      "--before", self.before, "--after", self.after])
        self.assertResult(result, 2, "the orig tree and the target tree must not contain each other")

    def test_missing_flags_and_folders(self):
        self.assertEqual(run([sys.executable, "-I", SCRIPT, "apply", "--before", self.before,
                              "--after", self.after]).returncode, 2)
        result = run([sys.executable, "-I", SCRIPT, "apply", "--orig", self.tmp / "nope", "--target", self.target,
                      "--before", self.before, "--after", self.after])
        self.assertResult(result, 2, "--orig is not a directory")
        self.assertResult(self.apply("--del", "notes/a.md"), 2, "unrecognized arguments: --del")

    def test_a_backup_with_no_file_of_the_glob(self):
        for path in sorted(self.before.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        self.assertResult(self.apply(), 2, "no files match '**/*.md' under", "(--before)")

    def test_a_path_that_is_not_printable(self):
        name = "notes/odd name.md"
        try:
            self.tree(self.orig, {name: "x\n"})
        except OSError as exc:
            self.skipTest(f"the file system refuses the name: {exc}")
        self.tree(self.after, {name: "x\n"})
        self.tree(self.before, {name: "x\n"})
        self.assertResult(self.apply(), 2, 'not printable: "notes/odd\\u2028name.md"')

    def test_help_names_the_subcommand_and_its_exit_codes(self):
        self.assertResult(run([sys.executable, "-I", SCRIPT, "--help"]), 0, "trim_report.py apply --help")
        self.assertResult(run([sys.executable, "-I", SCRIPT, "apply", "--help"]), 0,
                          "3 = refused, no file changed", "--delete PATH")


class ApplyFailureTests(ApplyCase):
    def test_a_failed_write_stops_the_run_and_a_second_run_ends_it(self):
        result = self.apply(prefix=("-c", FAIL_WRITE, "new.md"))
        self.assertResult(result, 4, "FAILED notes/new.md: the disk refuses the write", "CHANGED notes/a.md",
                          "RESULT: FAILED. 1 of 3 actions are done.")
        self.assertTrue((self.after / "notes/log/old.md").exists(), "a deletion ran after a failed write")
        result = self.apply()
        self.assertResult(result, 0, "APPLIED: 0 changed, 1 new, 1 deleted, 0 folders removed, 1 done before.",
                          "DONE BEFORE notes/a.md", "RESULT: PASS")


    def test_a_new_file_that_appears_during_the_run_is_kept(self):
        # Another process writes notes/new.md after the tests of the script and before its write.
        result = self.apply(prefix=("-c", APPEAR_ON_WRITE, "new.md"))
        self.assertResult(result, 4, "FAILED notes/new.md", "RESULT: FAILED. 1 of 3 actions are done.")
        self.assertEqual((self.after / "notes/new.md").read_bytes(), b"written by another process\n")


class ApplyOutputTests(ApplyCase):
    def test_a_long_output_is_cut_and_ends_with_the_result(self):
        many = {f"notes/many/f{n:03}.md": f"Text of REQ-{n + 100}.\n" for n in range(150)}
        for root in (self.after, self.before, self.orig):
            self.tree(root, many)
        self.tree(self.target, {path: text.replace("Text of", "Of") for path, text in many.items()})
        (self.after / "notes/keep.md").write_bytes(b"Keep it.\n")
        result = self.apply()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 102, result.stdout)
        self.assertTrue(lines[100].startswith("CUT: "), lines[100])
        self.assertEqual(lines[-1], "RESULT: FAIL")
        self.assertIn("- Missing: REQ-3", result.stdout, "a failed check must come before the file list")
        self.assertLessEqual(max(len(line) for line in lines), 250 + len(" ..."))
        self.assertLess(len(result.stdout), 30000)

    def test_a_long_line_is_cut(self):
        ids = " ".join(f"REQ-{n}" for n in range(200, 300))
        for root in (self.after, self.before, self.orig, self.target):
            self.tree(root, {"notes/ids.md": ids + "\n"})
        (self.after / "notes/ids.md").write_bytes(b"none\n")
        result = self.apply()
        missing = [line for line in result.stdout.splitlines() if line.startswith("- Missing: ")]
        self.assertEqual(len(missing), 1, result.stdout)
        self.assertTrue(missing[0].endswith(" ..."))
        self.assertEqual(len(missing[0]), 250 + len(" ..."))


if __name__ == "__main__":
    unittest.main()
