"""Tests for skills/trim-artifacts/scripts/trim_report.py.

Each test builds a before tree and an after tree in a temporary folder and runs
the script as a child process, as the skill does.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import REPO

SCRIPT = REPO / "essentials/dev-essentials/skills/trim-artifacts/scripts/trim_report.py"
DECISION = r"(?m)^## Decision \d+\n\nQuote: .*\nDecision: .*$"
NOTES = "# Notes\n\nREQ-1 and REQ-2 are open.\n\n## Decision 1\n\nQuote: keep it\nDecision: keep the cache\n"


class TrimReportCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
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
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=60)

    def assertResult(self, result, code, *texts):
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, output)
        for text in texts:
            self.assertIn(text, output)


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


if __name__ == "__main__":
    unittest.main()
