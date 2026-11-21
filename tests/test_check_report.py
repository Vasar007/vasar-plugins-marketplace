"""Tests for skills/bug-hunt/scripts/check_report.py.

Most tests import the script and call main() in this process. A stub replaces
the process scan, because the real scan on Windows takes seconds. The classes
ProcessListTests and RealProcessScanTests test the scan itself.

The Linux and macOS branch of list_processes() runs for real only on Linux or
macOS, for example in the Linux CI job. On other machines, a stub for `ps`
tests the parser. No test runs on macOS. The stub uses the `lstart` format,
which is the same on Linux and macOS (not confirmed on a macOS machine).
"""
import contextlib
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from support import REPO, load_module, tool_missing
from testkit import ScratchCase, git_init, remove_tree, run

SCRIPT = REPO / "essentials/dev-essentials/skills/bug-hunt/scripts/check_report.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bug-hunt"
cr = load_module("check_report", SCRIPT)
REAL_PROCESS_SCAN = cr.list_processes
MARKER = ".bug-hunt-scratch"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def edit(text, old, new):
    """Replace the first old with new. Fail if the text has no old."""
    if old not in text:
        raise AssertionError(f"the fixture has no {old!r}")
    return text.replace(old, new, 1)


SNAPSHOT_FILES = {"src/orders/export.ext": 142, "src/invoices/total.ext": 10, "src/invoices/retry.ext": 5}
DETAILS = "### New details for known issues\n\nNone.\n\n### BH-02"
LOCATION_LINE = "- Location: `src/orders/export.ext:142`"


def wrong_rows(count, wrong):
    """A final report with count entries. The first wrong rows have a severity that differs from the entry."""
    entry = ("### BH-{n:02d}: Entry {n}\n\n- Severity: High\n- Confidence: High\n- Category: Other: x\n"
             "- Location: `a.ext:1`\n- Also on base: No (new in the analyzed commit)\n- Verdict: Confirmed\n\n"
             "Problem: x.\n\nFailure scenario: x.\n\nEvidence: x.\n\nFix idea: x.\n\nVerification: x.\n\n")
    rows = "".join(f"| BH-{n:02d} | Entry {n} | Area 1 | {'Low' if n <= wrong else 'High'} | High | Confirmed | No |\n"
                   for n in range(1, count + 1))
    return (f"# Bug hunt report: p\n\n## Scope\n\nx\n\n## Summary\n\nFindings: {count}. Confirmed: {count}. "
            "Unconfirmed (needs owner review): 0. Rejected: 0. Duplicate: 0.\n\n"
            "| ID | Title | Area | Severity | Confidence | Verdict | Also on base |\n| --- | --- | --- | --- | --- | --- | --- |\n"
            f"{rows}\n### For the owner's review\n\nNone.\n\n## Known issues that this report does not repeat\n\nNone.\n\n"
            "## Area 1: All\n\n### New details for known issues\n\nNone.\n\n"
            + "".join(entry.format(n=n) for n in range(1, count + 1))
            + "### Notes for other areas\n\nNone.\n\n## Appendix: rejected findings\n\nNone yet.\n")


class CheckReportCase(ScratchCase):
    def setUp(self):
        super().setUp()
        self.report_dir = self.tmp / "report"
        self.report_dir.mkdir()
        self.scratch = self.tmp / "scratch"
        self.report = self.report_dir / "bug-hunt-report.md"
        stub = mock.patch.object(cr, "list_processes", return_value=[])
        stub.start()
        self.addCleanup(stub.stop)

    def write(self, text, newline="\n", bom=False):
        data = text.replace("\n", newline).encode("utf-8")
        self.report.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)

    def run_main(self, *args):
        """Run the script with args. Return the exit code and the output lines."""
        cr.problems.clear()
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["check_report.py", *map(str, args)]):
            with contextlib.redirect_stdout(out):
                code = cr.main()
        return code, out.getvalue().splitlines()

    def check(self, areas_done=2, stage="final", *extra):
        return self.run_main("report", "--report", self.report, "--scratch", self.scratch,
                             "--areas-done", areas_done, "--stage", stage, *extra)

    def check_text(self, text, *args):
        self.write(text)
        return self.check(*args)

    def assertPasses(self, result):
        code, lines = result
        self.assertEqual(code, 0, "\n".join(lines))

    def assertDefect(self, result, text):
        code, lines = result
        self.assertEqual(code, 1, "\n".join(lines))
        self.assertTrue(any(x.startswith("DEFECT: ") and text in x for x in lines),
                        f"no DEFECT line with {text!r}:\n" + "\n".join(lines))


class ValidReportTests(CheckReportCase):
    def test_skeleton_passes_before_the_first_search(self):
        code, lines = self.check_text(fixture("skeleton.md"), 0, "search")
        self.assertEqual(code, 0, lines)
        self.assertIn("INFO: findings=0 next=BH-01", lines[-1])

    def test_final_report_passes_at_every_late_stage(self):
        self.write(fixture("final.md"))
        for stage, extra in (("verify", ("--verified-to", "3")), ("summary", ()), ("final", ())):
            with self.subTest(stage=stage):
                code, lines = self.check(2, stage, *extra)
                self.assertEqual(code, 0, lines)
                self.assertIn("findings=3 next=BH-04 confirmed=1 unconfirmed=1 rejected=1", lines[-1])

    def test_crlf_line_ends(self):
        self.write(fixture("final.md"), newline="\r\n")
        self.assertPasses(self.check())

    def test_byte_order_mark(self):
        self.write(fixture("final.md"), bom=True)
        self.assertPasses(self.check())

    def test_headings_inside_tilde_and_backtick_fences_are_ignored(self):
        block = ("~~~text\n## Not a section\n### BH-99: Not an entry\n~~~\n\n"
                 "```text\n## Not a section either\n```\n\n")
        anchor = "### New details for known issues\n\nNone.\n\n### BH-01"
        text = edit(fixture("final.md"), anchor, anchor.replace("None.\n\n", "None.\n\n" + block))
        self.assertPasses(self.check_text(text))

    def test_base_no_drops_the_also_on_base_field(self):
        lines = fixture("final.md").split("\n")
        text = "\n".join(x for x in lines if not x.startswith("- Also on base:"))
        self.assertPasses(self.check_text(text, 2, "final", "--base", "no"))
        self.assertDefect(self.check_text(text, 2, "final", "--base", "yes"),
                          "BH-01: missing field 'Also on base'")

    def test_changed_severity_with_was_form_is_legal(self):
        text = edit(fixture("final.md"), "- Severity: High\n", "- Severity: Medium (was High)\n")
        text = edit(text, "| Area 1 | High | High |", "| Area 1 | Medium | High |")
        self.assertPasses(self.check_text(text))

    def test_final_report_passes_with_snapshots_that_hold_each_location(self):
        ref, base = self.tmp / "snapshot-ref", self.tmp / "snapshot-base"
        for root, path, lines in ((ref, "src/orders/export.ext", 142), (ref, "src/invoices/total.ext", 10),
                                  (ref, "src/invoices/retry.ext", 5), (base, "src/orders/export.ext", 139)):
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text("x\n" * lines, encoding="utf-8")
        self.write(fixture("final.md"))
        self.assertPasses(self.check(2, "final", "--snapshot", ref, "--base-snapshot", base))
        (base / "src/orders/export.ext").write_text("x\n" * 138, encoding="utf-8")
        self.assertDefect(self.check(2, "final", "--snapshot", ref, "--base-snapshot", base),
                          "BH-01: Also on base line 139 is past the end of src/orders/export.ext (138 lines)")


class ReferenceAndRowTests(CheckReportCase):
    """The tests of report that a verifier and the auditor used to make by hand: rows, references, and locations."""

    def snapshot(self, files, name="snapshot-ref"):
        root = self.tmp / name
        for path, lines in files.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text("x\n" * lines, encoding="utf-8")
        return root

    def defects(self, result):
        return [x for x in result[1] if x.startswith("DEFECT: ")]

    def duplicate_of(self, ref):
        text = edit(fixture("final.md"), "- Verdict: Unconfirmed (needs owner review)\n", f"- Verdict: Duplicate of {ref}\n")
        text = edit(text, "Rejected: 1. Duplicate: 0.", "Rejected: 1. Duplicate: 1.")
        text = edit(text, "Unconfirmed (needs owner review): 1.", "Unconfirmed (needs owner review): 0.")
        return edit(text, "| Unconfirmed (needs owner review) | No |", f"| Duplicate of {ref} | No |")

    def test_a_snapshot_option_that_names_no_folder_is_a_usage_error(self):
        self.write(fixture("final.md"))
        (self.tmp / "a-file").write_text("x\n", encoding="utf-8")
        for option in ("--snapshot", "--base-snapshot"):
            for value in (self.tmp / "no-such-folder", self.tmp / "a-file", ""):
                with self.subTest(option=option, value=str(value)):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as stop:
                        self.check(2, "final", option, value)
                    self.assertEqual(stop.exception.code, 2)
                    self.assertIn(f"argument {option}: not a folder", err.getvalue())

    def test_a_row_that_differs_from_its_entry_gives_one_defect(self):
        for label, old, new in (("Severity", "| Area 1 | High | High |", "| Area 1 | Low | High |"),
                                ("Confidence", "| Area 1 | High | High |", "| Area 1 | High | Low |"),
                                ("Verdict", "| High | High | Confirmed | Yes |", "| High | High | Rejected | Yes |"),
                                ("Also on base", "| Confirmed | Yes |", "| Confirmed | No |")):
            with self.subTest(label=label):
                code, lines = self.check_text(edit(fixture("final.md"), old, new))
                self.assertEqual([x for x in lines if x.startswith("DEFECT: ")],
                                 [x for x in lines if x.startswith(f"DEFECT: BH-01: Summary {label} ")])
                self.assertDefect((code, lines), f"BH-01: Summary {label} ")

    def test_a_row_with_the_new_value_of_a_changed_entry_passes(self):
        text = edit(fixture("final.md"), "- Confidence: Low\n", "- Confidence: Medium (was Low)\n")
        self.assertDefect(self.check_text(text), "BH-02: Summary Confidence 'Low' differs")
        self.assertPasses(self.check_text(edit(text, "| Medium | Low | Unconfirmed", "| Medium | Medium | Unconfirmed")))

    def test_a_row_with_the_old_value_passes(self):
        text = edit(fixture("final.md"), "- Severity: High\n", "- Severity: Medium (was High)\n")
        self.assertPasses(self.check_text(edit(text, "| Area 1 | High | High |", "| Area 1 | Medium (was High) | High |")))
        self.assertDefect(self.check_text(edit(text, "| Area 1 | High | High |", "| Area 1 | Low (was High) | High |")),
                          "BH-01: Summary Severity 'Low (was High)' differs")

    def test_a_table_with_no_base_column_does_not_stop_the_command(self):
        text = fixture("final.md").replace(" | Also on base |\n", " |\n").replace("| --- | --- |\n", "| --- |\n")
        for cell in ("Yes", "No"):
            text = text.replace(f" | {cell} |\n", " |\n")
        self.assertNotIn("| Yes |", text)
        self.assertPasses(self.check_text(text))

    def test_a_cell_that_is_not_a_value_of_the_format_passes(self):
        text = edit(fixture("final.md"), "- Also on base: Yes, `src/orders/export.ext:139`",
                    "- Also on base: Not applicable (the analyzed commit is the base)")
        for cell in ("Not applicable", "N/A", "-", "yes"):
            with self.subTest(cell=cell):
                self.assertPasses(self.check_text(edit(text, "| Confirmed | Yes |", f"| Confirmed | {cell} |")))
        self.assertPasses(self.check_text(edit(fixture("final.md"), "| Unconfirmed (needs owner review) |", "| Unconfirmed |")))
        self.assertDefect(self.check_text(edit(text, "| Confirmed | Yes |", "| Confirmed | No |")),
                          "BH-01: Summary Also on base 'No' differs")

    def test_a_row_with_no_last_pipe_is_read_to_its_last_cell(self):
        self.assertDefect(self.check_text(edit(fixture("final.md"), "| Confirmed | Yes |", "| Confirmed | No")),
                          "BH-01: Summary Also on base 'No' differs")
        self.assertPasses(self.check_text(edit(fixture("final.md"), "| Confirmed | Yes |", "| Confirmed | Yes")))

    def test_a_row_whose_area_differs_from_the_section_passes(self):
        self.assertPasses(self.check_text(edit(fixture("final.md"), "| Area 1 | High |", "| Area 2 | High |")))

    def test_a_duplicate_must_name_an_earlier_entry(self):
        text = edit(fixture("final.md"), "- Verdict: Unconfirmed (needs owner review)\n", "- Verdict: Duplicate of BH-03\n")
        text = edit(text, "Rejected: 1. Duplicate: 0.", "Rejected: 1. Duplicate: 1.")
        text = edit(text, "Unconfirmed (needs owner review): 1.", "Unconfirmed (needs owner review): 0.")
        text = edit(text, "| Unconfirmed (needs owner review) | No |", "| Duplicate of BH-03 | No |")
        self.assertDefect(self.check_text(text), "BH-02: Duplicate of BH-03 must name an earlier entry")
        itself = text.replace("Duplicate of BH-03", "Duplicate of BH-02")
        self.assertDefect(self.check_text(itself), "BH-02: Duplicate of BH-02 must name an earlier entry")
        earlier = text.replace("Duplicate of BH-03", "Duplicate of BH-01")
        self.assertPasses(self.check_text(earlier))

    def test_a_reference_to_a_known_issue_must_name_one_of_the_report(self):
        text = edit(fixture("final.md"), "### New details for known issues\n\nNone.\n\n### BH-02",
                    "### New details for known issues\n\n- New details for N-02: the same loop.\n\n### BH-02")
        self.assertDefect(self.check_text(text), "N-02 is not in the Known issues section")
        known = edit(text, "- #12: Slow export.", "- N-02: Slow import. Source: NOTES.md.\n- #12: Slow export.")
        self.assertPasses(self.check_text(known))

    def test_a_github_reference_must_be_in_the_digest(self):
        text = edit(fixture("final.md"), "### New details for known issues\n\nNone.\n\n### BH-02",
                    "### New details for known issues\n\n- New details for #12: one more case.\n\n### BH-02")
        code, lines = self.check_text(text)
        self.assertEqual(code, 0, lines)
        self.assertTrue(any(x.startswith("WARN: no known-issues digest") for x in lines), lines)
        self.scratch.mkdir()
        (self.scratch / "known-issues.md").write_text("# Known-issues digest\n\n- #7: Old bug.\n", encoding="utf-8")
        self.assertDefect(self.check_text(text), "#12 is not in the known-issues digest")
        (self.scratch / "known-issues.md").write_text("# Known-issues digest\n\n- #12: Slow export.\n", encoding="utf-8")
        self.assertPasses(self.check_text(text))

    def test_a_duplicate_of_a_known_issue_must_name_one_that_exists(self):
        text = self.duplicate_of("N-02")
        self.assertDefect(self.check_text(text), "BH-02: N-02 is not in the Known issues section")
        longer = edit(text, "- #12: Slow export.", "- N-020: Slow import. Source: NOTES.md.\n- #12: Slow export.")
        self.assertDefect(self.check_text(longer), "BH-02: N-02 is not in the Known issues section")
        self.assertPasses(self.check_text(edit(text, "- #12: Slow export.", "- N-02: Slow import. Source: NOTES.md.\n- #12: Slow export.")))
        issue = self.duplicate_of("#12")
        self.scratch.mkdir()
        (self.scratch / "known-issues.md").write_text("- #120: Other bug.\n- owner/repo#12: Other repository.\n", encoding="utf-8")
        self.assertDefect(self.check_text(issue), "BH-02: #12 is not in the known-issues digest")
        (self.scratch / "known-issues.md").write_text("- #12 (open): Slow export.\n", encoding="utf-8")
        self.assertPasses(self.check_text(issue))

    def test_a_missing_digest_gives_one_warn_line(self):
        text = edit(fixture("final.md"), DETAILS, DETAILS.replace("None.", "- New details for #12: a.\n- New details for #13: b."))
        code, lines = self.check_text(text)
        self.assertEqual(code, 0, lines)
        self.assertEqual(len([x for x in lines if x.startswith("WARN: no known-issues digest")]), 1, lines)

    def test_one_defect_line_for_a_reference_that_comes_more_than_once(self):
        text = edit(fixture("final.md"), DETAILS, DETAILS.replace("None.", "- New details for N-09: a.\n- New details for N-09: b."))
        self.assertEqual(self.defects(self.check_text(text)), ["DEFECT: N-09 is not in the Known issues section"])

    def test_an_entry_id_of_another_report_in_prose_passes(self):
        text = edit(fixture("final.md"), "- #12: Slow export.",
                    "- N-01: Wrong tax (BH-17 of the report of May). Source: notes file `old.md`.\n- #12: Slow export.")
        text = edit(text, "- Analyzed code:", "- Round 2. Round 1 found BH-01 to BH-23.\n- Analyzed code:")
        self.assertPasses(self.check_text(text))

    def test_an_entry_id_in_a_place_of_the_format_must_name_an_entry(self):
        self.assertDefect(self.check_text(edit(fixture("final.md"), "Result: BH-02.", "Result: BH-09.")),
                          "the report names BH-09, but no entry has this ID")
        self.assertPasses(self.check_text(edit(fixture("final.md"), "Result: BH-02.", "Result: `BH-09`.")))
        self.assertDefect(self.check_text(edit(fixture("final.md"), "- BH-02: decide", "- BH-08: decide")),
                          "the report names BH-08, but no entry has this ID")
        self.assertDefect(self.check_text(self.duplicate_of("BH-07")), "the report names BH-07, but no entry has this ID")

    def test_a_location_must_name_a_file_and_a_line_of_the_snapshot(self):
        self.write(fixture("final.md"))
        root = self.snapshot({"src/orders/export.ext": 141, "src/invoices/retry.ext": 5})
        code, lines = self.check(2, "final", "--snapshot", root)
        self.assertDefect((code, lines), "BH-01: Location line 142 is past the end of src/orders/export.ext (141 lines)")
        self.assertDefect((code, lines), "BH-02: Location names a file that the snapshot does not hold: src/invoices/total.ext")
        self.assertEqual(len([x for x in lines if x.startswith("DEFECT: ")]), 2, lines)
        text = edit(fixture("final.md"), "- Location: `src/invoices/retry.ext:5`", "- Location: `src/invoices/retry.ext:4-6`")
        self.assertDefect(self.check_text(text, 2, "final", "--snapshot", root),
                          "BH-03: Location line 6 is past the end of src/invoices/retry.ext (5 lines)")

    def test_a_location_out_of_the_snapshot_is_a_defect_and_is_not_read(self):
        root = self.snapshot(SNAPSHOT_FILES)
        (self.tmp / "outside.ext").write_text("x\n" * 500, encoding="utf-8")
        for path in ("../outside.ext", str(self.tmp / "outside.ext"), "/outside.ext", "\\outside.ext", "C:\\outside.ext",
                     "C:/outside.ext", "C:outside.ext", "//host/share/outside.ext"):
            with self.subTest(path=path), mock.patch.object(cr, "read", wraps=cr.read) as reads:
                text = edit(fixture("final.md"), LOCATION_LINE, f"- Location: `{path}:142`")
                self.assertDefect(self.check_text(text, 2, "final", "--snapshot", root),
                                  f"BH-01: Location path leaves the snapshot: {path}")
                self.assertNotIn("outside.ext", " ".join(str(call.args[0]) for call in reads.call_args_list))

    def test_a_link_out_of_the_snapshot_is_a_defect_and_is_not_read(self):
        root = self.snapshot(SNAPSHOT_FILES)
        (self.tmp / "outside.ext").write_text("x\n" * 7, encoding="utf-8")
        try:
            os.symlink(self.tmp / "outside.ext", root / "link.ext")
            os.symlink(self.tmp, root / "folder-link", target_is_directory=True)
            os.symlink(root / "src/invoices/retry.ext", root / "inside-link.ext")
        except OSError as error:
            self.skipTest(f"no right to make a link: {error}")
        for path in ("link.ext", "folder-link/outside.ext"):
            with self.subTest(path=path), mock.patch.object(cr, "read", wraps=cr.read) as reads:
                text = edit(fixture("final.md"), LOCATION_LINE, f"- Location: `{path}:99`")
                self.assertDefect(self.check_text(text, 2, "final", "--snapshot", root),
                                  f"BH-01: Location path leaves the snapshot through a link: {path}")
                self.assertNotIn("outside.ext", " ".join(str(call.args[0]) for call in reads.call_args_list))
        text = edit(fixture("final.md"), LOCATION_LINE, "- Location: `inside-link.ext:5`")
        self.assertPasses(self.check_text(text, 2, "final", "--snapshot", root))

    def test_a_path_with_a_space_is_read(self):
        root = self.snapshot(dict(SNAPSHOT_FILES, **{"src/my folder/a b.ext": 5}))
        text = edit(fixture("final.md"), LOCATION_LINE, "- Location: `src/my folder/a b.ext:5`")
        self.assertPasses(self.check_text(text, 2, "final", "--snapshot", root))
        text = edit(fixture("final.md"), LOCATION_LINE, "- Location: `src/my folder/a b.ext:6`")
        self.assertDefect(self.check_text(text, 2, "final", "--snapshot", root),
                          "BH-01: Location line 6 is past the end of src/my folder/a b.ext (5 lines)")

    def test_a_path_with_backslashes_gives_the_same_result_on_each_system(self):
        root = self.snapshot(SNAPSHOT_FILES)
        text = edit(fixture("final.md"), LOCATION_LINE, "- Location: `src\\orders\\export.ext:142`")
        self.assertPasses(self.check_text(text, 2, "final", "--snapshot", root))
        text = edit(fixture("final.md"), LOCATION_LINE, "- Location: `src\\orders\\export.ext:143`")
        self.assertDefect(self.check_text(text, 2, "final", "--snapshot", root),
                          "BH-01: Location line 143 is past the end of src\\orders\\export.ext (142 lines)")

    def test_a_line_part_that_is_not_a_line_or_a_range_is_a_defect(self):
        root = self.snapshot(SNAPSHOT_FILES)
        for part in ("0", "9-3", "142:7"):
            with self.subTest(part=part):
                text = edit(fixture("final.md"), LOCATION_LINE, f"- Location: `src/orders/export.ext:{part}`")
                result = self.check_text(text, 2, "final", "--snapshot", root)
                self.assertDefect(result, f"BH-01: Location is not in the form path:line or path:line-line: src/orders/export.ext:{part}")
                self.assertEqual(len(self.defects(result)), 1, result[1])

    def test_a_last_line_with_no_line_end_counts(self):
        root = self.snapshot(SNAPSHOT_FILES)
        self.write(fixture("final.md"))
        (root / "src/invoices/retry.ext").write_bytes(b"x\r\n" * 4 + b"x")
        self.assertPasses(self.check(2, "final", "--snapshot", root))
        (root / "src/invoices/retry.ext").write_bytes(b"x\r\n" * 4)
        self.assertDefect(self.check(2, "final", "--snapshot", root),
                          "BH-03: Location line 5 is past the end of src/invoices/retry.ext (4 lines)")
        (root / "src/invoices/retry.ext").write_bytes(b"")
        self.assertDefect(self.check(2, "final", "--snapshot", root),
                          "BH-03: Location line 5 is past the end of src/invoices/retry.ext (0 lines)")

    def test_a_base_answer_other_than_yes_is_not_read(self):
        ref, base = self.snapshot(SNAPSHOT_FILES), self.snapshot({"src/orders/export.ext": 139}, "snapshot-base")
        text = edit(fixture("final.md"), "- Also on base: No (new in the analyzed commit)",
                    "- Also on base: Not compared (`src/invoices/total.ext:10` is new)")
        text = edit(text, "| Unconfirmed (needs owner review) | No |", "| Unconfirmed (needs owner review) | Not compared |")
        self.assertPasses(self.check_text(text, 2, "final", "--snapshot", ref, "--base-snapshot", base))

    def test_the_appendix_with_entries_must_not_say_none_yet(self):
        text = edit(fixture("final.md"), "## Appendix: rejected findings\n\n", "## Appendix: rejected findings\n\nNone yet.\n\n")
        self.assertDefect(self.check_text(text), "the appendix holds entries and still says 'None yet.'")
        self.assertPasses(self.check_text(text, 2, "summary"))

    def test_none_yet_in_a_code_block_of_a_rejected_entry_passes(self):
        text = edit(fixture("final.md"), "Evidence: `retry.ext:5` loops on failure.",
                    "Evidence: the notes file says:\n\n```text\nNone yet.\n```")
        self.assertPasses(self.check_text(text))
        text = edit(fixture("final.md"), "## Appendix: rejected findings\n\n", "## Appendix: rejected findings\n\nNone yet. \n\n")
        self.assertDefect(self.check_text(text), "the appendix holds entries and still says 'None yet.'")

    def test_at_most_one_hundred_defect_lines_and_a_count_line(self):
        code, lines = self.check_text(wrong_rows(150, 150), 1, "final")
        defects = [x for x in lines if x.startswith("DEFECT: ")]
        self.assertEqual(code, 1)
        self.assertEqual(len(defects), 101, defects[-3:])
        self.assertEqual(defects[-1], "DEFECT: more defects that this output does not show: 50. "
                                      "Fix the defects above, then run the check again")

    def test_exactly_one_hundred_defects_give_no_count_line(self):
        result = self.check_text(wrong_rows(100, 100), 1, "final")
        self.assertEqual(result[0], 1)
        self.assertEqual(len(self.defects(result)), 100)
        self.assertTrue(self.defects(result)[-1].startswith("DEFECT: BH-100: Summary Severity"), self.defects(result)[-1])
        defects = self.defects(self.check_text(wrong_rows(101, 101), 1, "final"))
        self.assertEqual(len(defects), 101)
        self.assertEqual(defects[-1], "DEFECT: more defects that this output does not show: 1. "
                                      "Fix the defects above, then run the check again")


class StructureDefectTests(CheckReportCase):
    def test_wrong_title(self):
        text = fixture("final.md").replace("# Bug hunt report: ", "# Report: ", 1)
        self.assertDefect(self.check_text(text), "first line is not")

    def test_sections_out_of_order(self):
        text = fixture("skeleton.md")
        scope, summary, known = (text.index(h) for h in ("## Scope", "## Summary", "## Known issues"))
        text = text[:scope] + text[summary:known] + text[scope:summary] + text[known:]
        self.assertDefect(self.check_text(text, 0, "search"), "H2 sections missing or out of order")

    def test_empty_values(self):
        for label in ("Severity", "Confidence", "Verdict"):
            with self.subTest(label=label):
                old = next(x for x in fixture("final.md").split("\n") if x.startswith(f"- {label}: "))
                text = fixture("final.md").replace(old, f"- {label}:", 1)
                self.assertDefect(self.check_text(text), f"BH-01: {label} value is empty")

    def test_illegal_values(self):
        cases = (("- Severity: High\n", "- Severity: Severe\n", "Severity value 'Severe' is not legal"),
                 ("- Confidence: High\n", "- Confidence: Sure\n", "Confidence value 'Sure' is not legal"),
                 ("- Verdict: Confirmed\n", "- Verdict: Fixed\n", "Verdict value 'Fixed' is not legal"))
        for old, new, message in cases:
            with self.subTest(new=new):
                self.assertDefect(self.check_text(fixture("final.md").replace(old, new, 1)), message)

    def test_missing_field(self):
        text = fixture("final.md").replace("Fix idea: Loop to `count`.", "", 1)
        self.assertDefect(self.check_text(text), "BH-01: missing field 'Fix idea'")

    def test_id_gap_and_short_id(self):
        gap = fixture("final.md").replace("BH-03", "BH-04")
        self.assertDefect(self.check_text(gap), "IDs are not unique or not contiguous")
        short = fixture("final.md").replace("### BH-01:", "### BH-1:", 1).replace("| BH-01 |", "| BH-1 |", 1)
        self.assertDefect(self.check_text(short), "BH-1: ID has fewer than two digits")

    def test_pending_verdict_after_verification(self):
        text = fixture("final.md").replace("- Verdict: Confirmed", "- Verdict: Pending verification", 1)
        self.assertDefect(self.check_text(text, 2, "verify", "--verified-to", "1"),
                          "BH-01: verdict is still pending")

    def test_missing_verification_paragraph(self):
        text = fixture("final.md").replace("Verification: I ran the export", "Note: I ran the export", 1)
        self.assertDefect(self.check_text(text), "BH-01: missing field 'Verification'")

    def test_rejected_entry_outside_the_appendix(self):
        text = fixture("final.md").replace("- Verdict: Confirmed", "- Verdict: Rejected", 1)
        self.assertDefect(self.check_text(text), "BH-01: Rejected entry outside the appendix")

    def test_appendix_entry_that_is_not_rejected(self):
        text = fixture("final.md").replace("- Verdict: Rejected", "- Verdict: Confirmed", 1)
        self.assertDefect(self.check_text(text), "BH-03: entry in the appendix is not Rejected")

    def test_unconfirmed_entry_without_its_three_lines(self):
        for label in ("Not covered", "Where I looked", "To decide"):
            with self.subTest(label=label):
                text = fixture("final.md").replace(f"\n{label}: ", "\nRemoved: ", 1)
                self.assertDefect(self.check_text(text),
                                  f"BH-02: Unconfirmed entry has no '{label}:' line")

    def test_area_state_against_areas_done(self):
        result = self.check_text(fixture("skeleton.md"), 1, "search")
        self.assertDefect(result, "Area 1 still pending")
        self.assertDefect(result, "Known issues section still pending")
        self.assertDefect(self.check_text(fixture("final.md"), 1, "verify"), "Area 2 filled before its search")
        no_sub = fixture("final.md").replace("### Notes for other areas\n\nNone.", "", 1)
        self.assertDefect(self.check_text(no_sub), "Area 2 has no 'Notes for other areas' subsection")

    def test_known_issues_filled_too_early(self):
        text = fixture("skeleton.md").replace("Pending the first search.", "- #12: Slow export.", 1)
        self.assertDefect(self.check_text(text, 0, "search"),
                          "Known issues section filled before the first search")

    def test_control_character(self):
        text = fixture("final.md").replace("The loop stops", "The loop\x07 stops", 1)
        self.assertDefect(self.check_text(text), "control character in the report")

    def test_summary_count_line(self):
        wrong = fixture("final.md").replace("Findings: 3.", "Findings: 4.", 1)
        self.assertDefect(self.check_text(wrong), "Summary says 4 findings, the report has 3")
        counts = fixture("final.md").replace("Confirmed: 1. Unconfirmed", "Confirmed: 2. Unconfirmed", 1)
        self.assertDefect(self.check_text(counts), "Summary verdict counts do not match the entries")
        missing = fixture("final.md").replace("Findings: 3.", "Findings are below.", 1)
        self.assertDefect(self.check_text(missing), "Summary has no count line")

    def test_summary_table(self):
        order = fixture("final.md").replace("| BH-01 | Export", "| BH-09 | Export", 1)
        self.assertDefect(self.check_text(order), "Summary table rows do not match the IDs")
        title = fixture("final.md").replace("| BH-01 | Export drops the last order |",
                                            "| BH-01 | Export drops orders |", 1)
        self.assertDefect(self.check_text(title), "BH-01: Summary title differs from the heading")

    def test_final_stage_only_checks(self):
        no_review = fixture("final.md").replace("### For the owner's review", "### Owner notes", 1)
        self.assertPasses(self.check_text(no_review, 2, "summary"))
        self.assertDefect(self.check_text(no_review, 2, "final"), "no 'For the owner's review' subsection")
        placeholder = fixture("final.md").replace("Out of scope: none.", "Out of scope: {EXCLUDED}.", 1)
        self.assertDefect(self.check_text(placeholder), "placeholder left: {EXCLUDED}")
        quoted = edit(fixture("final.md"), "Out of scope: none.", "Out of scope: `{EXCLUDED}`.")
        self.assertPasses(self.check_text(quoted))

    def test_open_note_without_result(self):
        note = "- For Area 1 (Orders): `src/orders/a.ext:3`: look at the rounding."
        text = fixture("final.md").replace("### Notes for other areas\n\nNone.",
                                           "### Notes for other areas\n\n" + note, 1)
        self.assertDefect(self.check_text(text), "open note in Area 2")
        code, lines = self.run_main("open-notes", "--report", self.report)
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("For Area 1 (written in Area 2, line "), lines)
        self.assertTrue(lines[0].endswith(note), lines)

    def test_open_notes_ignores_a_note_inside_a_fence(self):
        fenced = "~~~\n- For Area 1 (Orders): `src/orders/a.ext:3`: look at the rounding.\n~~~"
        text = edit(fixture("final.md"), "### Notes for other areas\n\nNone.",
                    "### Notes for other areas\n\n" + fenced)
        self.write(text)
        self.assertEqual(self.run_main("open-notes", "--report", self.report), (0, []))

    def test_open_notes_ignores_a_note_inside_an_indented_fence(self):
        fenced = "  ~~~\n- For Area 1 (Orders): `src/orders/a.ext:3`: look at the rounding.\n  ~~~"
        text = edit(fixture("final.md"), "### Notes for other areas\n\nNone.",
                    "### Notes for other areas\n\n" + fenced)
        self.write(text)
        self.assertEqual(self.run_main("open-notes", "--report", self.report), (0, []))

    def test_an_inline_triple_backtick_span_opens_no_fence(self):
        lines = [line for line, fence in cr.fenced("   ```a``` text\n## Next\nbody") if fence]
        self.assertEqual(lines, [])

    def test_a_fence_that_closes_with_an_indent_ends_at_that_line(self):
        marks = [fence for _, fence in cr.fenced("```\ncode\n  ```\n## Next")]
        self.assertEqual(marks, [True, True, True, False])

    def test_a_placeholder_inside_a_tilde_fence_is_no_defect(self):
        text = edit(fixture("final.md"), "### Notes for other areas\n\nNone.",
                    "### Notes for other areas\n\nNone.\n\n~~~\nPending search.\n~~~")
        code, lines = self.check_text(text)
        self.assertEqual(code, 0, lines)


class ArtifactTests(CheckReportCase):
    def setUp(self):
        super().setUp()
        self.entry = self.report_dir / "bug-hunt-artifacts" / "BH-01"
        self.entry.mkdir(parents=True)
        (self.entry / "repro.md").write_text("Run the export.\n", encoding="utf-8")
        link = "- Artifacts: [bug-hunt-artifacts/BH-01/repro.md](bug-hunt-artifacts/BH-01/repro.md)\n"
        self.write(fixture("final.md").replace("- Verdict: Confirmed\n", "- Verdict: Confirmed\n" + link, 1))

    def test_valid_artifact_folder(self):
        code, lines = self.check()
        self.assertEqual(code, 0, lines)
        self.assertIn("artifact_folders=1", lines[-1])

    def test_link_that_does_not_resolve(self):
        (self.entry / "repro.md").rename(self.entry / "steps.md")
        result = self.check()
        self.assertDefect(result, "BH-01: artifact link does not resolve")
        self.assertDefect(result, "no repro.md in BH-01")

    def test_folder_and_file_rules(self):
        cases = {
            "artifact folder without an entry: BH-07": lambda: (self.entry.parent / "BH-07").mkdir(),
            "file outside an entry folder in bug-hunt-artifacts: notes.txt":
                lambda: (self.entry.parent / "notes.txt").write_text("x"),
            "build output folder in artifacts: BH-01/bin": lambda: (self.entry / "bin").mkdir(),
            "binary file in artifacts: BH-01/data.bin": lambda: (self.entry / "data.bin").write_bytes(b"a\x00b"),
            "artifact file larger than 1 MB: BH-01/big.txt":
                lambda: (self.entry / "big.txt").write_bytes(b"a" * (1024 * 1024 + 1)),
            "control character in BH-01/notes.md": lambda: (self.entry / "notes.md").write_bytes(b"a\x07b"),
        }
        for message, make in cases.items():
            with self.subTest(message=message):
                make()
                self.assertDefect(self.check(), message)

    def test_scratch_path_in_artifact_file(self):
        (self.entry / "log.txt").write_text(f"output in {self.scratch}{os.sep}work\n", encoding="utf-8")
        self.assertDefect(self.check(), "scratch path in artifact file: BH-01/log.txt")


class ScratchPathFormTests(unittest.TestCase):
    def test_windows_path_gets_every_slash_and_drive_form(self):
        forms = cr.drive_forms(r"C:\Users\dev\scratch")
        self.assertLessEqual({r"c:\users\dev\scratch", "c:/users/dev/scratch", "/c/users/dev/scratch"}, forms)

    def test_git_bash_path_gets_the_drive_form(self):
        forms = cr.drive_forms("/c/Users/dev/scratch/")
        self.assertLessEqual({"c:/users/dev/scratch", r"c:\users\dev\scratch"}, forms)

    def test_tmp_mount_form_under_temp(self):
        with mock.patch.dict(os.environ, {"TEMP": r"C:\Users\dev\AppData\Local\Temp"}):
            forms = cr.path_forms(r"C:\Users\dev\AppData\Local\Temp\bh-1")
        self.assertIn("/tmp/bh-1", forms)

    def test_short_temp_is_ignored(self):
        with mock.patch.dict(os.environ, {"TEMP": "C:\\", "TMP": ""}):
            forms = cr.path_forms(r"C:\scratch")
        self.assertFalse(any(f.startswith("/tmp") for f in forms))


class ProgressAndCommandTests(CheckReportCase):
    def test_progress_files(self):
        self.write(fixture("final.md"))
        (self.report_dir / "_bug-hunt-session-progress.md").write_text("x")
        self.assertPasses(self.check())
        (self.report_dir / "_bug-hunt-hunter-2.md").write_text("x")
        self.assertDefect(self.check(), "progress file left: _bug-hunt-hunter-2.md")
        self.assertPasses(self.check(2, "final", "--allow", "_bug-hunt-hunter-2.md"))

    def test_files_left_in_work_folder_warn_only(self):
        self.write(fixture("final.md"))
        (self.scratch / "work" / "hunter-1").mkdir(parents=True)
        (self.scratch / "work" / "hunter-1" / "a.txt").write_text("x")
        code, lines = self.check()
        self.assertEqual(code, 0, lines)
        self.assertIn("WARN: files left in work folder hunter-1", lines)

    def test_next_id(self):
        self.write(fixture("final.md"))
        self.assertEqual(self.run_main("next-id", "--report", self.report), (0, ["BH-04"]))
        self.write(fixture("skeleton.md"))
        self.assertEqual(self.run_main("next-id", "--report", self.report), (0, ["BH-01"]))

    def test_next_id_ignores_an_entry_heading_inside_a_fence(self):
        fenced = "Verification: I ran the export on three orders and got two rows.\n"
        text = edit(fixture("final.md"), fenced, fenced + "\n~~~\n### BH-99: Not an entry\n~~~\n")
        self.write(text)
        _, lines = self.check()
        self.assertIn("next=BH-04", lines[-1])
        self.assertEqual(self.run_main("next-id", "--report", self.report), (0, ["BH-04"]))

    def test_setup(self):
        args = ("setup", "--report-dir", self.report_dir, "--scratch", self.scratch)
        result = self.run_main(*args, "--base", "yes")
        self.assertDefect(result, "snapshot missing or empty")
        self.assertDefect(result, "known-issues digest missing or empty")
        for name in ("snapshot-ref", "snapshot-base"):
            (self.scratch / name).mkdir(parents=True)
            (self.scratch / name / "file.txt").write_text("x")
        (self.scratch / "known-issues.md").write_text("# Known-issues digest\n")
        self.assertEqual(self.run_main(*args, "--base", "yes"), (0, []))
        shutil.rmtree(self.scratch / "snapshot-base")
        self.assertDefect(self.run_main(*args, "--base", "yes"), "snapshot missing or empty")
        self.assertEqual(self.run_main(*args, "--base", "no"), (0, []))

    def test_cleanup(self):
        args = ("cleanup", "--report-dir", self.report_dir, "--scratch", self.scratch)
        self.scratch.mkdir()
        self.assertDefect(self.run_main(*args), "scratch folder still exists")
        self.scratch.rmdir()
        self.assertEqual(self.run_main(*args), (0, []))


class ProcessListTests(unittest.TestCase):
    def fake_run(self, stdout):
        done = subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")
        return mock.patch.object(cr.subprocess, "run", return_value=done)

    def test_windows_branch_parses_tab_separated_records(self):
        out = ("10\t4\t2026-10-15T09:00:00\tpython3 serve.py --dir C:\\scratch\n"
               "11\t10\t\t\n"
               "bad line\n")
        with mock.patch.object(cr.os, "name", "nt"), self.fake_run(out) as run:
            records = cr.list_processes()
        self.assertEqual(run.call_args.args[0][0], "powershell.exe")
        self.assertEqual(records, [(10, 4, "2026-10-15T09:00:00", "python3 serve.py --dir C:\\scratch"),
                                   (11, 10, "", "")])

    def test_ps_branch_parses_lstart_records(self):
        out = ("  123     1 Wed Oct 15 09:00:00 2026 python3 -m http.server --directory /tmp/bh-1\n"
               "  124   123 Wed Oct 15 09:01:00 2026 sleep 60\n"
               "short line\n")
        with mock.patch.object(cr.os, "name", "posix"), self.fake_run(out) as run:
            records = cr.list_processes()
        self.assertEqual(run.call_args.args[0], ["ps", "-eo", "pid=,ppid=,lstart=,args="])
        self.assertEqual(records, [
            (123, 1, "Wed Oct 15 09:00:00 2026", "python3 -m http.server --directory /tmp/bh-1"),
            (124, 123, "Wed Oct 15 09:01:00 2026", "sleep 60")])

    def test_failed_command_gives_none(self):
        done = subprocess.CompletedProcess([], 1, stdout="", stderr="ps: error")
        with mock.patch.object(cr.subprocess, "run", return_value=done):
            self.assertIsNone(cr.list_processes())

    def test_missing_command_gives_none(self):
        with mock.patch.object(cr.subprocess, "run", side_effect=FileNotFoundError("ps")):
            self.assertIsNone(cr.list_processes())

    def test_leftovers_warns_for_a_process_that_uses_the_scratch_folder(self):
        scratch = r"C:\work\bh-scratch"
        # A fixed own pid, so that a real pid such as 501 cannot clash with the fake records.
        records = [(100, 99, "", f"python3 runner.py {scratch}"),
                   (99, 98, "", f"bash -c cd {scratch}"),
                   (98, 1, "", f"claude --add-dir {scratch}"),
                   (500, 1, "2026-10-15T09:00:00", "dotnet test C:/work/bh-scratch/app.sln"),
                   (501, 1, "", f"python3 check_report.py --scratch {scratch}"),
                   (502, 1, "", "unrelated")]
        out = io.StringIO()
        with mock.patch.object(cr.os, "getpid", return_value=100), mock.patch.object(cr.Path, "is_dir", return_value=False):
            with mock.patch.object(cr, "list_processes", return_value=records), contextlib.redirect_stdout(out):
                cr.leftovers(scratch)
        self.assertEqual(out.getvalue().splitlines(), [
            "WARN: process uses the scratch folder: pid=500 started=2026-10-15T09:00:00 "
            "command=dotnet test C:/work/bh-scratch/app.sln"])

    def test_leftovers_warns_when_processes_cannot_be_listed(self):
        out = io.StringIO()
        with mock.patch.object(cr.Path, "is_dir", return_value=False):
            with mock.patch.object(cr, "list_processes", return_value=None), contextlib.redirect_stdout(out):
                cr.leftovers(r"C:\work\bh-scratch")
        self.assertEqual(out.getvalue().splitlines(), ["WARN: cannot list processes"])


class RealProcessScanTests(unittest.TestCase):
    """The real scan of this machine: PowerShell on Windows, ps on Linux and macOS."""

    def test_scan_finds_this_process(self):
        records = cr.list_processes()
        if records is None:
            tool_missing(self, "the process list command (PowerShell or ps) is not available")
        parents = {pid: ppid for pid, ppid, _, _ in records}
        self.assertEqual(parents.get(os.getpid()), os.getppid())


class CommandLineTests(unittest.TestCase):
    def run_script(self, *args):
        return run([sys.executable, "-I", SCRIPT, *args], timeout=120)

    def test_usage_error_exits_with_2(self):
        self.assertEqual(self.run_script().returncode, 2)
        self.assertEqual(self.run_script("report", "--report", "r.md").returncode, 2)

    def test_exit_code_1_on_a_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "bug-hunt-report.md"
            report.write_text("# Wrong title\n", encoding="utf-8")
            result = self.run_script("report", "--report", report, "--scratch", Path(tmp) / "s",
                                     "--areas-done", "0", "--stage", "search")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("DEFECT: first line is not", result.stdout)


class GitCase(CheckReportCase):
    """A test case with a git repository in self.repo. The repository has no commit yet."""

    def setUp(self):
        super().setUp()
        self.repo = git_init(self.tmp / "repo")
        self.git(self.repo, "config", "core.autocrlf", "false")

    def git(self, repo, *args):
        return run(["git", "-C", repo, *args], check=True).stdout.strip()

    def commit(self, files, links=(), message="change"):
        """Write and commit files, a dict of name to bytes. Each link (name, target) goes in with no file on disk."""
        for name, data in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if files:
            self.git(self.repo, "add", "--", *files)
        for name, target in links:
            blob = run(["git", "-C", self.repo, "hash-object", "-w", "--stdin"], stdin=target, check=True).stdout.strip()
            self.git(self.repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},{name}")
        self.git(self.repo, "commit", "-q", "-m", message)
        return self.git(self.repo, "rev-parse", "HEAD")

    def link(self, path, target, folder=False):
        try:
            Path(path).symlink_to(target, target_is_directory=folder)
        except OSError as error:
            self.skipTest(f"no right to make a link: {error}")

    def assertRefused(self, result, text):
        code, lines = result
        self.assertEqual(code, 2, "\n".join(lines))
        self.assertTrue(any(line.startswith("REFUSED: ") and text in line for line in lines),
                        f"no REFUSED line with {text!r}:\n" + "\n".join(lines))


class SnapshotTests(GitCase):
    FILES = {"README.md": b"# Shop\n", "src/orders/export.py": b"rows = []\r\n", "data/logo.bin": b"\x00\x01\xff"}

    def snapshot(self, sha, *extra, scratch=None):
        return self.run_main("snapshot", "--repo", self.repo, "--ref-sha", sha, "--scratch", scratch or self.scratch,
                             *(extra or ("--base-from", "none")))

    def test_ref_snapshot_holds_each_tracked_file_with_its_bytes(self):
        sha = self.commit(self.FILES)
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        for name, data in self.FILES.items():
            self.assertEqual((self.scratch / "snapshot-ref" / name).read_bytes(), data, name)
        self.assertTrue((self.scratch / "work").is_dir() and (self.scratch / "tools").is_dir())
        self.assertTrue((self.scratch / MARKER).is_file())
        self.assertIn(f"SNAPSHOT: ref {self.scratch / 'snapshot-ref'} files=3 git=3", lines)
        self.assertIn("SNAPSHOT: base none (no base comparison)", lines)

    def test_folder_that_holds_files_and_no_marker_is_refused(self):
        sha = self.commit(self.FILES)
        (self.scratch / "work" / "shop").mkdir(parents=True)
        (self.scratch / "work" / "shop" / "notes.txt").write_text("mine")
        before = sorted(self.tmp.rglob("*"))
        self.assertRefused(self.snapshot(sha), f"is not empty and has no {MARKER} file")
        self.assertEqual(sorted(self.tmp.rglob("*")), before)

    def test_folder_with_the_marker_and_another_entry_is_refused(self):
        sha = self.commit(self.FILES)
        self.scratch.mkdir()
        (self.scratch / MARKER).write_text("x")
        (self.scratch / "src").mkdir()
        before = sorted(self.tmp.rglob("*"))
        self.assertRefused(self.snapshot(sha), "entries that a bug hunt does not make: src")
        self.assertEqual(sorted(self.tmp.rglob("*")), before)

    def test_marker_that_is_a_link_or_a_folder_is_refused(self):
        sha = self.commit(self.FILES)
        outside = self.tmp / "outside.txt"
        outside.write_text("keep")
        for form in ("folder", "link"):
            with self.subTest(form=form):
                self.scratch.mkdir()
                if form == "folder":
                    (self.scratch / MARKER).mkdir()
                else:
                    self.link(self.scratch / MARKER, outside)
                self.assertRefused(self.snapshot(sha), "is not a regular file")
                self.assertEqual(outside.read_text(), "keep")
                self.assertEqual(os.listdir(self.scratch), [MARKER])
                shutil.rmtree(self.scratch)

    def test_marker_that_is_a_hard_link_keeps_the_text_of_its_other_name(self):
        sha = self.commit(self.FILES)
        outside = self.tmp / "outside.txt"
        outside.write_text("keep this text")
        self.scratch.mkdir()
        try:
            os.link(outside, self.scratch / MARKER)
        except OSError as error:
            self.skipTest(f"this file system has no hard links: {error}")
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertEqual(outside.read_text(), "keep this text")

    def test_archive_whose_end_block_ends_a_record_is_read_to_its_end(self):
        sha = self.commit({"a.txt": b"x" * 8000})
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertIn(f"SNAPSHOT: ref {self.scratch / 'snapshot-ref'} files=1 git=1", lines)

    def test_commit_with_no_files_gives_an_empty_snapshot(self):
        self.git(self.repo, "commit", "-q", "--allow-empty", "-m", "empty")
        code, lines = self.snapshot(self.git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(code, 0, lines)
        self.assertIn(f"SNAPSHOT: ref {self.scratch / 'snapshot-ref'} files=0 git=0", lines)

    def test_failed_snapshot_leaves_a_folder_that_delete_temp_removes(self):
        sha = self.commit(self.FILES)
        code, lines = self.snapshot(sha, "--base-from", "remote", "--base-branch", "main",
                                    "--base-url", (self.tmp / "missing.git").as_uri())
        self.assertEqual(code, 1, lines)
        code, lines = self.run_main("delete-temp", "--report-dir", self.report_dir, "--scratch", self.scratch,
                                    "--repo", self.repo, "--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(os.path.lexists(self.scratch))

    def test_home_folder_and_temp_root_are_refused(self):
        sha = self.commit(self.FILES)
        cases = (({"HOME": str(self.scratch), "USERPROFILE": str(self.scratch)}, None, "is the home folder"),
                 ({}, str(self.scratch), "is the temp root"))
        for env, temp, text in cases:
            with self.subTest(text=text):
                with mock.patch.dict(os.environ, env), \
                        mock.patch.object(cr.tempfile, "gettempdir", return_value=temp or tempfile.gettempdir()):
                    self.assertRefused(self.snapshot(sha), text)
                self.assertFalse(self.scratch.exists())

    def test_snapshot_reads_no_work_tree_file_and_keeps_the_index(self):
        sha = self.commit(self.FILES)
        (self.repo / "README.md").write_bytes(b"# Changed\n")
        (self.repo / "untracked.txt").write_bytes(b"new\n")
        status = self.git(self.repo, "status", "--porcelain")
        index = os.stat(self.repo / ".git" / "index").st_mtime_ns
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertEqual((self.scratch / "snapshot-ref" / "README.md").read_bytes(), b"# Shop\n")
        self.assertFalse((self.scratch / "snapshot-ref" / "untracked.txt").exists())
        self.assertEqual(os.stat(self.repo / ".git" / "index").st_mtime_ns, index)
        self.assertEqual(self.git(self.repo, "status", "--porcelain"), status)

    def test_local_base_with_the_same_sha_makes_no_base_snapshot(self):
        sha = self.commit(self.FILES)
        code, lines = self.snapshot(sha, "--base-from", "local", "--base-sha", sha)
        self.assertEqual(code, 0, lines)
        self.assertFalse((self.scratch / "snapshot-base").exists())
        self.assertIn("SNAPSHOT: base none (the analyzed commit is the base)", lines)

    def test_local_base_with_another_sha_exports_that_commit(self):
        base = self.commit(self.FILES)
        ref = self.commit({"README.md": b"# Shop 2\n"})
        code, lines = self.snapshot(ref, "--base-from", "local", "--base-sha", base)
        self.assertEqual(code, 0, lines)
        self.assertEqual((self.scratch / "snapshot-ref" / "README.md").read_bytes(), b"# Shop 2\n")
        self.assertEqual((self.scratch / "snapshot-base" / "README.md").read_bytes(), b"# Shop\n")
        self.assertIn(f"SNAPSHOT: base {self.scratch / 'snapshot-base'} sha={base} files=3 git=3", lines)

    def remote(self):
        """Commit the files, make a branch release with one more commit, and a bare copy. Return its URL and SHAs."""
        ref = self.commit(self.FILES)
        self.git(self.repo, "switch", "-q", "-c", "release")
        head = self.commit({"README.md": b"# Release\n"})
        self.git(self.repo, "switch", "-q", "-")
        run(["git", "clone", "-q", "--bare", self.repo, self.tmp / "origin.git"], check=True)
        return (self.tmp / "origin.git").as_uri(), ref, head

    def test_remote_base_with_a_relative_scratch_folder_lands_in_that_folder(self):
        url, ref, head = self.remote()
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.tmp)
        code, lines = self.snapshot(ref, "--base-from", "remote", "--base-branch", "release", "--base-url", url,
                                    scratch="scratch")
        self.assertEqual(code, 0, lines)
        self.assertTrue((self.scratch / "snapshot-base" / "README.md").is_file(), lines)

    def test_remote_base_clones_the_branch_and_prints_its_head(self):
        url, ref, head = self.remote()
        code, lines = self.snapshot(ref, "--base-from", "remote", "--base-branch", "release", "--base-url", url)
        self.assertEqual(code, 0, lines)
        self.assertIn(f"SNAPSHOT: base {self.scratch / 'snapshot-base'} sha={head} files=3 git=3", lines)
        self.assertEqual((self.scratch / "snapshot-base" / "README.md").read_bytes(), b"# Release\n")

    def test_snapshot_bytes_do_not_follow_core_autocrlf_of_the_user(self):
        url, ref, head = self.remote()
        config = self.tmp / "gitconfig"
        config.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
        self.git(self.repo, "config", "--unset", "core.autocrlf")
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
            code, lines = self.snapshot(ref, "--base-from", "remote", "--base-branch", "release", "--base-url", url)
        self.assertEqual(code, 0, lines)
        self.assertEqual((self.scratch / "snapshot-ref" / "README.md").read_bytes(), b"# Shop\n")
        self.assertEqual((self.scratch / "snapshot-base" / "README.md").read_bytes(), b"# Release\n")

    def test_remote_base_with_export_ignore_names_the_files_that_only_the_base_holds(self):
        ref = self.commit({**self.FILES, ".gitattributes": b"docs/** export-ignore\n", "docs/guide.md": b"# Guide\n"})
        self.git(self.repo, "branch", "release")
        run(["git", "clone", "-q", "--bare", self.repo, self.tmp / "origin.git"], check=True)
        code, lines = self.snapshot(ref, "--base-from", "remote", "--base-branch", "release",
                                    "--base-url", (self.tmp / "origin.git").as_uri())
        self.assertEqual(code, 0, lines)
        base = [line for line in lines if line.startswith("LIMIT: base snapshot: export-ignore")]
        self.assertEqual(len(base), 1, lines)
        self.assertIn("clone", base[0])
        self.assertTrue((self.scratch / "snapshot-base" / "docs" / "guide.md").is_file())
        self.assertFalse((self.scratch / "snapshot-ref" / "docs" / "guide.md").exists())

    def test_url_that_starts_with_a_dash_reaches_git_as_a_url(self):
        sha = self.commit(self.FILES)
        code, lines = self.snapshot(sha, "--base-from", "remote", "--base-branch", "main", "--base-url=-oops")
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(line.startswith("ERROR: git clone") and "'-oops'" in line for line in lines), lines)
        self.assertFalse((self.scratch / "snapshot-base").exists())

    def test_scratch_folder_inside_or_around_the_repository_is_refused(self):
        sha = self.commit(self.FILES)
        for scratch in (self.repo / "scratch", self.tmp):
            with self.subTest(scratch=scratch):
                before = sorted(self.tmp.rglob("*"))
                self.assertRefused(self.snapshot(sha, scratch=scratch), "the repository folder")
                self.assertEqual(sorted(self.tmp.rglob("*")), before)

    def test_snapshot_folder_that_is_not_empty_is_refused(self):
        sha = self.commit(self.FILES)
        for name in ("snapshot-ref", "snapshot-base"):
            with self.subTest(name=name):
                (self.scratch / name).mkdir(parents=True)
                (self.scratch / MARKER).write_text("x")
                (self.scratch / name / "old.txt").write_text("old")
                self.assertRefused(self.snapshot(sha), f"{name} exists and is not an empty folder")
                self.assertEqual(sorted(p.name for p in self.scratch.iterdir()), sorted([MARKER, name]))
                shutil.rmtree(self.scratch)

    def test_snapshot_folder_that_is_a_link_is_refused(self):
        sha = self.commit(self.FILES)
        outside = self.tmp / "outside"
        outside.mkdir()
        self.scratch.mkdir()
        (self.scratch / MARKER).write_text("x")
        self.link(self.scratch / "snapshot-ref", outside, folder=True)
        self.assertRefused(self.snapshot(sha), "snapshot-ref exists and is not an empty folder")
        self.assertEqual(list(outside.iterdir()), [])

    def test_short_ref_sha_and_a_scratch_path_that_is_a_file_are_refused(self):
        sha = self.commit(self.FILES)
        self.assertRefused(self.snapshot(sha[:12]), "--ref-sha is not a full commit SHA")
        self.assertFalse(self.scratch.exists())
        self.scratch.write_text("a file")
        self.assertRefused(self.snapshot(sha), "is not a folder")
        self.assertEqual(self.scratch.read_text(), "a file")

    def test_base_commit_that_does_not_exist_gives_exit_1_and_creates_nothing(self):
        sha = self.commit(self.FILES)
        code, lines = self.snapshot(sha, "--base-from", "local", "--base-sha", "1" * 40)
        self.assertEqual(code, 1, lines)
        self.assertFalse(self.scratch.exists())

    def test_file_in_the_place_of_the_work_folder_gives_an_error_line(self):
        sha = self.commit(self.FILES)
        self.scratch.mkdir()
        (self.scratch / MARKER).write_text("x")
        (self.scratch / "work").write_text("a file")
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(line.startswith("ERROR: FileExistsError") for line in lines), lines)

    def test_missing_or_short_values_are_refused(self):
        sha = self.commit(self.FILES)
        cases = ((("--base-from", "local"), "--base-from local needs --base-sha"),
                 (("--base-from", "remote", "--base-branch", "main"), "--base-from remote needs --base-branch and"),
                 (("--base-from", "local", "--base-sha", sha[:12]), "--base-sha is not a full commit SHA"))
        for extra, text in cases:
            with self.subTest(text=text):
                self.assertRefused(self.snapshot(sha, *extra), text)
                self.assertFalse(self.scratch.exists())

    def test_submodules_export_ignore_and_lfs_give_limit_lines(self):
        sha = self.commit({**self.FILES, ".gitmodules": b'[submodule "lib"]\n\tpath = lib\n\turl = ../lib\n',
                           ".gitattributes": b"docs/** export-ignore\n*.psd filter=lfs diff=lfs merge=lfs -text\n",
                           "docs/guide.md": b"# Guide\n"})
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        limits = [line for line in lines if line.startswith("LIMIT: ref snapshot: ")]
        for word in ("submodules", "export-ignore", "filter=lfs"):
            self.assertEqual(len([line for line in limits if word in line]), 1, lines)
        self.assertFalse((self.scratch / "snapshot-ref" / "docs" / "guide.md").exists())
        self.assertTrue(any(line.startswith("WARN: the ref snapshot has 5 files, and git lists 6") for line in lines),
                        lines)

    def test_link_to_an_absolute_path_gives_a_limit_line_and_the_rest_lands(self):
        outside = self.tmp / "outside.txt"
        outside.write_text("secret")
        sha = self.commit(self.FILES, links=[("abs", str(outside))])
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertTrue(any(line.startswith("LIMIT: ref snapshot: abs is not in the snapshot") for line in lines),
                        lines)
        self.assertFalse(os.path.lexists(self.scratch / "snapshot-ref" / "abs"))
        self.assertEqual((self.scratch / "snapshot-ref" / "src/orders/export.py").read_bytes(), b"rows = []\r\n")

    def test_link_that_the_system_cannot_make_gives_a_limit_line_and_the_rest_lands(self):
        sha = self.commit({**self.FILES, "zz.txt": b"last\n"}, links=[("docs-link", "README.md")])
        with mock.patch.object(cr.os, "symlink", side_effect=OSError("no right to make a link")):
            code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertTrue(any(line.startswith("LIMIT: ref snapshot: docs-link is not in the snapshot")
                            for line in lines), lines)
        self.assertFalse(os.path.lexists(self.scratch / "snapshot-ref" / "docs-link"))
        self.assertEqual((self.scratch / "snapshot-ref" / "zz.txt").read_bytes(), b"last\n")

    def test_link_inside_the_commit_lands_and_counts_as_one_file(self):
        self.link(self.tmp / "probe-link", self.tmp, folder=True)
        sha = self.commit(self.FILES, links=[("docs-link", "README.md"), ("src-link", "src")])
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertEqual(lines, [f"SNAPSHOT: ref {self.scratch / 'snapshot-ref'} files=5 git=5",
                                 "SNAPSHOT: base none (no base comparison)"])
        self.assertTrue(os.path.islink(self.scratch / "snapshot-ref" / "src-link"))

    def test_nested_gitattributes_counts_and_a_comment_line_does_not(self):
        sha = self.commit({**self.FILES, ".gitattributes": b"# *.psd filter=lfs\n",
                           "src/.gitattributes": b"*.gen export-ignore\n"})
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        limits = [line for line in lines if line.startswith("LIMIT: ")]
        self.assertEqual(len(limits), 1, lines)
        self.assertIn("export-ignore", limits[0])

    def test_names_that_differ_only_by_case_keep_the_bytes_of_each_path(self):
        for name, data in (("README.md", b"first\n"), ("readme.md", b"second\n")):
            blob = run(["git", "-C", self.repo, "hash-object", "-w", "--stdin"], stdin=data, check=True, text=False)
            self.git(self.repo, "update-index", "--add", "--cacheinfo", f"100644,{blob.stdout.decode().strip()},{name}")
        self.git(self.repo, "commit", "-q", "-m", "two names")
        code, lines = self.snapshot(self.git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(code, 0, lines)
        ref = self.scratch / "snapshot-ref"
        self.assertEqual((ref / "README.md").read_bytes(), b"first\n")
        if sorted(os.listdir(ref)) == ["README.md", "readme.md"]:
            self.assertEqual((ref / "readme.md").read_bytes(), b"second\n")
        else:
            self.assertTrue(any(line.startswith("LIMIT: ref snapshot: readme.md is not in the snapshot")
                                for line in lines), lines)

    def test_commit_that_does_not_exist_gives_exit_1_and_the_git_error(self):
        self.commit(self.FILES)
        code, lines = self.snapshot("0" * 40)
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(line.startswith("ERROR: git rev-parse --verify ") and "fatal:" in line
                            for line in lines), lines)
        self.assertFalse(self.scratch.exists())

    def test_output_has_at_most_40_lines(self):
        outside = str(self.tmp / "outside.txt")
        sha = self.commit(self.FILES, links=[(f"link{i:02d}", outside) for i in range(60)])
        code, lines = self.snapshot(sha)
        self.assertEqual(code, 0, lines)
        self.assertEqual(len(lines), 40, lines)
        self.assertEqual(lines[-1], "... 24 more lines")
        self.assertTrue(lines[0].startswith("SNAPSHOT: ref "), lines)


class DeleteTempTests(GitCase):
    """delete-temp on a scratch folder with the layout of a run, and a report folder with the files of a run."""

    KEPT = ("bug-hunt-report.md", "bug-hunt-context.md", "bug-hunt-artifacts/BH-01/repro.md",
            "_bug-hunt-session-progress.md", "notes.md")
    PROGRESS = ("_bug-hunt-progress-orders.md", "_bug-hunt-progress-audit.md")

    def setUp(self):
        super().setUp()
        self.commit({"README.md": b"# Shop\n"})
        self.layout(self.scratch)
        for name in self.KEPT + self.PROGRESS:
            path = self.report_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")

    @staticmethod
    def layout(folder):
        """Write the files of a run into folder, with the marker of the snapshot command."""
        for name in ("snapshot-ref/README.md", "snapshot-base/README.md", "work/hunter-1/log.txt", "tools/x.txt",
                     "known-issues.md", MARKER):
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")

    def delete(self, *extra, scratch=None, repo=None, report_dir=None):
        return self.run_main("delete-temp", "--report-dir", report_dir or self.report_dir,
                             "--scratch", scratch or self.scratch, "--repo", repo or self.repo, *extra)

    def tree(self, folder=None):
        """Each path below folder, without a walk into a link."""
        found = []
        for top, dirs, files in os.walk(folder or self.tmp):
            found += [os.path.join(top, name) for name in dirs + files]
        return sorted(found)

    def test_without_apply_nothing_changes(self):
        before = self.tree()
        code, lines = self.delete()
        self.assertEqual(code, 0, lines)
        self.assertEqual(self.tree(), before)
        expected = [f"WOULD DELETE: {path}" for path in [self.scratch] + sorted(
            self.report_dir / name for name in self.PROGRESS)]
        self.assertEqual(lines, expected)

    def test_apply_deletes_the_scratch_folder_with_read_only_files(self):
        objects = self.scratch / "snapshot-base" / ".git" / "objects" / "ab"
        objects.mkdir(parents=True)
        (objects / "cdef").write_text("blob")
        os.chmod(objects / "cdef", stat.S_IREAD)
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(self.scratch.exists())
        self.assertIn(f"DELETED: {self.scratch}", lines)

    def test_apply_keeps_the_report_files_and_deletes_only_progress_files(self):
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        for name in self.KEPT:
            self.assertTrue((self.report_dir / name).is_file(), name)
        for name in self.PROGRESS:
            self.assertFalse((self.report_dir / name).exists(), name)

    def test_apply_gives_exit_1_when_the_cleanup_check_finds_a_left_file(self):
        (self.report_dir / "_bug-hunt-hunter-2.md").write_text("x")
        code, lines = self.delete("--apply")
        self.assertEqual(code, 1, lines)
        self.assertIn("DEFECT: progress file left: _bug-hunt-hunter-2.md", lines)

    def test_delete_that_fails_gives_exit_1_and_failed_lines(self):
        real_unlink = Path.unlink

        def unlink(path, *args, **kwargs):
            if path.name == self.PROGRESS[0]:
                raise PermissionError("denied")
            return real_unlink(path, *args, **kwargs)

        def delete_tree(path, *args, **kwargs):
            return ["work: denied"] if os.path.basename(path) == "work" else []

        with mock.patch.object(cr, "delete_tree", delete_tree), mock.patch.object(Path, "unlink", unlink):
            code, lines = self.delete("--apply")
        self.assertEqual(code, 1, lines)
        self.assertIn(f"FAILED: {self.scratch}: work: denied", lines)
        self.assertIn(f"FAILED: {self.report_dir / self.PROGRESS[0]}: denied", lines)
        self.assertTrue(self.scratch.is_dir())

    def test_delete_that_fails_keeps_the_marker_and_a_second_run_finishes(self):
        real_delete_tree = cr.delete_tree

        def delete_tree(path, *args, **kwargs):
            if os.path.basename(path) == "work":
                return ["work: denied"]
            return real_delete_tree(path, *args, **kwargs)

        with mock.patch.object(cr, "delete_tree", delete_tree):
            code, lines = self.delete("--apply")
        self.assertEqual(code, 1, lines)
        self.assertTrue((self.scratch / MARKER).is_file(), lines)
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertIn(f"DELETED: {self.scratch}", lines)
        self.assertFalse(os.path.lexists(self.scratch))

    def test_empty_folder_without_the_marker_is_deleted(self):
        shutil.rmtree(self.scratch)
        self.scratch.mkdir()
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertIn(f"DELETED: {self.scratch}", lines)
        self.assertFalse(os.path.lexists(self.scratch))

    def test_failed_line_names_the_path_inside_the_scratch_folder_and_the_reason(self):
        scratch = self.tmp / ("s" * 130)
        self.layout(scratch)
        real_unlink = os.unlink

        def unlink(path, *args, **kwargs):
            if os.path.basename(path) == "log.txt":
                raise PermissionError("denied")
            return real_unlink(path, *args, **kwargs)

        with mock.patch.object(cr.os, "unlink", unlink):
            code, lines = self.delete("--apply", scratch=scratch)
        self.assertEqual(code, 1, lines)
        failed = [line for line in lines if line.startswith(f"FAILED: {scratch}: ")]
        self.assertEqual(len(failed), 1, lines)
        self.assertIn(f"{os.path.join('work', 'hunter-1', 'log.txt')}: denied", failed[0])

    def test_failed_line_names_the_folder_itself_in_words(self):
        folder = self.tmp / "empty"
        folder.mkdir()
        real_rmdir = os.rmdir

        def rmdir(path, *args, **kwargs):
            if os.path.abspath(path) == str(folder):
                raise PermissionError("denied")
            return real_rmdir(path, *args, **kwargs)

        with mock.patch.object(cr.os, "rmdir", rmdir):
            errors = cr.delete_tree(folder)
        # shutil of POSIX adds the path to the error, so only the name part is fixed.
        self.assertEqual(len(errors), 1, errors)
        self.assertTrue(errors[0].startswith("the folder itself: "), errors)

    def test_read_only_file_at_the_top_is_deleted(self):
        path = self.scratch / "known-issues.md"
        os.chmod(path, stat.S_IREAD)
        self.addCleanup(lambda: path.exists() and os.chmod(path, stat.S_IWRITE | stat.S_IREAD))
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertIn(f"DELETED: {self.scratch}", lines)

    @unittest.skipIf(os.name == "nt", "a folder with no write right keeps no file on Windows")
    def test_scratch_folder_with_no_write_right_is_deleted(self):
        self.addCleanup(lambda: self.scratch.exists() and os.chmod(self.scratch, stat.S_IRWXU))
        os.chmod(self.scratch, stat.S_IRUSR | stat.S_IXUSR)
        code, lines = self.delete_without_dac_rights("--apply")
        self.assertEqual(code, 0, lines)
        self.assertIn(f"DELETED: {self.scratch}", lines)

    def delete_without_dac_rights(self, *extra):
        """Run delete-temp in a child process. As root, capsh drops the rights that ignore the folder modes."""
        prefix = []
        if os.geteuid() == 0:
            capsh = shutil.which("capsh")
            if not capsh:
                self.skipTest("root ignores folder rights")
            prefix = [capsh, "--drop=cap_dac_override,cap_dac_read_search", "--", "-c", 'exec "$0" "$@"']
        # A copy in the temp folder, because root with no DAC rights cannot pass a closed home folder of the clone.
        script = shutil.copy(SCRIPT, self.tmp / "check_report.py")
        result = run(prefix + [sys.executable, "-I", script, "delete-temp", "--report-dir", self.report_dir,
                               "--scratch", self.scratch, "--repo", self.repo, *extra], timeout=120)
        return result.returncode, (result.stdout + result.stderr).splitlines()

    @unittest.skipIf(os.name == "nt", "a folder with no write right keeps no file on Windows")
    def test_apply_deletes_a_folder_with_no_write_right(self):
        cache = self.scratch / "work" / "hunter-1" / "mod" / "pkg@v1.0.0"
        cache.mkdir(parents=True)
        (cache / "pkg.go").write_text("package pkg")

        def restore():
            for path in (cache.parent, cache):
                if path.exists():
                    os.chmod(path, stat.S_IRWXU)

        self.addCleanup(restore)
        for path in (cache, cache.parent):
            os.chmod(path, stat.S_IRUSR | stat.S_IXUSR)
        code, lines = self.delete_without_dac_rights("--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(self.scratch.exists())

    def test_scratch_folder_or_its_parent_that_becomes_a_link_after_the_guards_is_not_deleted(self):
        run_folder = self.tmp / "run"
        scratch = run_folder / "scratch"
        victim = self.tmp / "victim"
        (victim / "scratch").mkdir(parents=True)
        (victim / "scratch" / "keep.txt").write_text("keep")

        def junction(path, target):
            if os.name == "nt":
                run(["cmd", "/c", "mklink", "/J", path, target], check=True)
            else:
                os.symlink(target, path)

        for swapped, target in ((scratch, victim / "scratch"), (run_folder, victim)):
            with self.subTest(swapped=swapped.name):
                self.layout(scratch)

                def swap(a, out):
                    os.rename(swapped, self.tmp / "old")
                    junction(swapped, target)
                    return []

                with mock.patch.object(cr, "processes_to_stop", swap):
                    code, lines = self.delete("--apply", scratch=scratch)
                self.assertEqual(code, 1, lines)
                self.assertTrue(any(line.startswith(f"FAILED: {scratch}: ") for line in lines), lines)
                self.assertEqual((victim / "scratch" / "keep.txt").read_text(), "keep")
                (os.rmdir if os.name == "nt" else os.unlink)(swapped)
                remove_tree(self.tmp / "old")
                if swapped == scratch:
                    remove_tree(run_folder)

    def test_empty_or_relative_scratch_path_and_a_short_option_are_refused(self):
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.tmp)
        before = self.tree()
        self.assertRefused(self.delete("--apply", scratch="scratch"), "must be an absolute path")
        self.assertEqual(self.tree(), before)
        cases = (["--report-dir", self.report_dir, "--scratch", self.scratch, "--a"],
                 ["--report-dir", self.report_dir, "--scratch", "", "--apply"],
                 ["--report-dir", "", "--scratch", self.scratch, "--apply"])
        for extra in cases:
            with self.subTest(extra=extra[:4]):
                # In the report folder, an empty --report-dir names a real report folder to pathlib.
                result = run([sys.executable, "-I", SCRIPT, "delete-temp", "--repo", self.repo, *extra],
                             cwd=self.report_dir, timeout=120)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(self.tree(), before)

    def test_report_folder_that_does_not_exist_is_refused(self):
        before = self.tree()
        self.assertRefused(self.delete("--apply", report_dir=self.tmp / "reprot"), "reprot is not a folder")
        self.assertEqual(self.tree(), before)

    def test_output_is_utf_8_also_with_another_code_page(self):
        scratch = self.tmp / "Zoë-проба"
        self.scratch.rename(scratch)
        result = run([sys.executable, "-I", "-X", "utf8=0", SCRIPT, "delete-temp", "--report-dir", self.report_dir,
                      "--scratch", scratch, "--repo", self.repo], timeout=120)
        self.assertResult(result, 0, f"WOULD DELETE: {scratch}")

    def test_scratch_folder_in_the_repository_is_refused(self):
        inside = self.repo / "scratch"
        shutil.copytree(self.scratch, inside)
        before = self.tree()
        self.assertRefused(self.delete("--apply", scratch=inside), "is inside the repository folder")
        self.assertEqual(self.tree(), before)

    def test_scratch_folder_and_report_folder_that_meet_are_refused(self):
        for report_dir, text in ((self.scratch / "work" / "reports", "holds the report folder"),
                                 (self.scratch, "is the report folder"),
                                 (self.report_dir, "is inside the report folder")):
            with self.subTest(text=text):
                scratch = self.report_dir / "scratch" if text.endswith("inside the report folder") else self.scratch
                scratch.mkdir(exist_ok=True)
                report_dir.mkdir(exist_ok=True)
                before = self.tree()
                self.assertRefused(self.delete("--apply", scratch=scratch, report_dir=report_dir), text)
                self.assertEqual(self.tree(), before)

    def test_home_folder_and_temp_root_are_refused(self):
        home = self.scratch / "work" / "user"
        home.mkdir()
        cases = (({"HOME": str(self.scratch), "USERPROFILE": str(self.scratch)}, None, "is the home folder"),
                 ({"HOME": str(home), "USERPROFILE": str(home)}, None, "holds the home folder"),
                 ({}, str(self.scratch), "is the temp root"))
        for env, temp, text in cases:
            with self.subTest(text=text):
                before = self.tree()
                with mock.patch.dict(os.environ, env), \
                        mock.patch.object(cr.tempfile, "gettempdir", return_value=temp or tempfile.gettempdir()):
                    self.assertRefused(self.delete("--apply"), text)
                self.assertEqual(self.tree(), before)

    def test_each_form_of_the_home_folder_is_refused(self):
        other = self.tmp / "other-home"
        other.mkdir()
        for env in ({"HOME": str(self.scratch), "USERPROFILE": str(other)},
                    {"HOME": str(other), "USERPROFILE": str(self.scratch)}):
            with self.subTest(env=env):
                with mock.patch.dict(os.environ, env):
                    self.assertRefused(self.delete(), "is the home folder")

    def test_drive_root_is_refused(self):
        root = Path(self.tmp.anchor)
        self.assertRefused(self.delete(scratch=root), "is a drive root or a mount point")

    def test_mount_point_as_or_inside_the_scratch_folder_is_refused(self):
        for point in (self.scratch, self.scratch / "work"):
            with self.subTest(point=point.name):
                before = self.tree()
                with mock.patch.object(cr, "mount_points", return_value=[os.path.realpath(point)]):
                    self.assertRefused(self.delete("--apply"), "is or holds the mount point")
                self.assertEqual(self.tree(), before)
        with mock.patch.object(cr, "mount_points", return_value=[os.path.realpath(self.scratch) + "-2"]):
            code, lines = self.delete()
        self.assertEqual(code, 0, lines)
        self.assertFalse(any(line.startswith("REFUSED") for line in lines), lines)

    def test_scratch_path_that_is_a_file_is_refused(self):
        shutil.rmtree(self.scratch)
        self.scratch.write_text("a file")
        self.assertRefused(self.delete("--apply"), "is not a folder")
        self.assertEqual(self.scratch.read_text(), "a file")

    @unittest.skipIf(os.name == "nt", "a folder with no read right exists only on POSIX")
    def test_folder_that_the_walk_cannot_read_is_refused(self):
        closed = self.scratch / "work" / "closed"
        closed.mkdir()
        os.chmod(closed, 0)
        self.addCleanup(os.chmod, closed, stat.S_IRWXU)
        self.assertRefused(self.delete_without_dac_rights("--apply"), "cannot read the folder")
        self.assertTrue(closed.is_dir())

    def test_folder_without_the_marker_is_refused(self):
        dev = self.tmp / "dev"
        shop = git_init(dev / "work" / "shop")
        run(["git", "-C", shop, "commit", "-q", "--allow-empty", "-m", "unpushed"], check=True)
        (dev / "tools").mkdir()
        (dev / "tools" / "script.sh").write_text("echo")
        (self.scratch / MARKER).unlink()
        for scratch in (dev, self.scratch):
            with self.subTest(scratch=scratch.name):
                before = self.tree()
                self.assertRefused(self.delete("--apply", scratch=scratch), f"has no {MARKER} file")
                self.assertEqual(self.tree(), before)

    def test_marker_that_is_a_link_or_a_folder_is_refused(self):
        outside = self.tmp / "outside.txt"
        outside.write_text("keep")
        marker = self.scratch / MARKER
        marker.unlink()
        marker.mkdir()
        before = self.tree()
        self.assertRefused(self.delete("--apply"), f"has no {MARKER} file")
        self.assertEqual(self.tree(), before)
        marker.rmdir()
        self.link(marker, outside)
        before = self.tree()
        self.assertRefused(self.delete("--apply"), f"has no {MARKER} file")
        self.assertEqual(self.tree(), before)
        self.assertEqual(outside.read_text(), "keep")

    def test_scratch_folder_that_is_a_link_is_refused(self):
        link = self.tmp / "scratch-link"
        self.link(link, self.scratch, folder=True)
        before = self.tree()
        self.assertRefused(self.delete("--apply", scratch=link), "is a link or a junction")
        self.assertEqual(self.tree(), before)

    def test_link_inside_the_scratch_folder_goes_and_its_target_stays(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep")
        self.link(self.scratch / "work" / "file-link", outside / "keep.txt")
        self.link(self.scratch / "work" / "folder-link", outside, folder=True)
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(os.path.lexists(self.scratch))
        self.assertEqual((outside / "keep.txt").read_text(), "keep")

    @unittest.skipUnless(os.name == "nt", "a junction exists only on Windows")
    def test_junction_as_the_scratch_folder_or_inside_it(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep")
        (outside / ".git").write_text("gitdir: " + str(self.tmp / "elsewhere" / ".git"))
        junction = self.tmp / "scratch-junction"
        run(["cmd", "/c", "mklink", "/J", junction, self.scratch], check=True)
        before = self.tree()
        self.assertRefused(self.delete("--apply", scratch=junction), "is a link or a junction")
        self.assertEqual(self.tree(), before)
        os.rmdir(junction)
        run(["cmd", "/c", "mklink", "/J", self.scratch / "work" / "linked", outside], check=True)
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(os.path.lexists(self.scratch))
        self.assertEqual((outside / "keep.txt").read_text(), "keep")

    def test_scratch_folder_in_another_worktree_of_the_repository_is_refused(self):
        linked = self.tmp / "linked"
        self.git(self.repo, "worktree", "add", "-q", "-b", "side", linked)
        bare = self.tmp / "bare.git"
        run(["git", "clone", "-q", "--bare", self.repo, bare], check=True)
        relative = self.tmp / "relative"
        made = run(["git", "-C", self.repo, "-c", "worktree.useRelativePaths=true", "worktree", "add", "-q", "-b",
                    "rel", relative])
        cases = ((linked / "scratch", self.repo, "the repository folder"),
                 (self.repo / "scratch", linked, "the repository folder"),
                 (bare / "scratch", bare, "the repository folder"),
                 (relative / "scratch", self.repo, "the repository folder"))
        for scratch, repo, text in cases:
            with self.subTest(scratch=scratch.relative_to(self.tmp), repo=repo.name):
                if scratch.parent == relative and made.returncode != 0:
                    self.skipTest(f"this git has no relative worktree paths: {made.stderr.strip()}")
                shutil.copytree(self.scratch, scratch)
                before = self.tree()
                result = self.delete("--apply", scratch=scratch, repo=repo)
                self.assertRefused(result, text)
                self.assertFalse(any(".." in line for line in result[1]), result[1])
                self.assertEqual(self.tree(), before)

    def test_worktree_inside_the_scratch_folder_is_refused(self):
        other = git_init(self.tmp / "other")
        run(["git", "-C", other, "commit", "-q", "--allow-empty", "-m", "start"], check=True)
        for source, text in ((other, "is a worktree or a repository whose git folder is outside"),
                             (self.repo, "holds the repository folder")):
            with self.subTest(source=source.name):
                inner = self.scratch / "work" / f"wt-{source.name}"
                self.git(source, "worktree", "add", "-q", "--detach", inner)
                (inner / "draft.txt").write_text("work in progress")
                self.assertRefused(self.delete("--apply"), text)
                self.assertEqual((inner / "draft.txt").read_text(), "work in progress")
                self.git(source, "worktree", "remove", "--force", inner)

    def test_clone_that_the_run_made_inside_the_scratch_folder_is_deleted(self):
        clone = self.scratch / "tools" / "lib"
        run(["git", "clone", "-q", self.repo, clone], check=True)
        self.git(clone, "worktree", "add", "-q", "--detach", self.scratch / "work" / "lib-wt")
        run(["git", "clone", "-q", "--bare", self.repo, self.scratch / "tools" / "lib.git"], check=True)
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(self.scratch.exists())

    def test_git_folder_whose_core_worktree_has_quotes_is_refused(self):
        outside = self.tmp / "user#fix"
        outside.mkdir()
        lib = self.scratch / "tools" / "lib" / ".git"
        lib.parent.mkdir()
        run(["git", f"--git-dir={lib}", f"--work-tree={outside}", "init", "-q"], check=True)
        self.assertIn('"', (lib / "config").read_text(encoding="utf-8"))
        before = self.tree()
        self.assertRefused(self.delete("--apply"), "has the worktree")
        self.assertEqual(self.tree(), before)

    def test_git_folder_with_a_worktree_outside_the_scratch_folder_is_refused(self):
        def clone_in_tools(scratch, outside):
            clone = scratch / "tools" / "lib"
            run(["git", "clone", "-q", self.repo, clone], check=True)
            self.git(clone, "worktree", "add", "-q", "-b", "fix", outside)

        def bare_in_work(scratch, outside):
            bare = scratch / "work" / "hunter-1" / "shop.git"
            run(["git", "clone", "-q", "--bare", self.repo, bare], check=True)
            self.git(bare, "worktree", "add", "-q", "-b", "fix", outside)

        def separate_git_folder_in_tools(scratch, outside):
            run(["git", "init", "-q", "--separate-git-dir", scratch / "tools" / "sep.git", outside], check=True)

        for make in (clone_in_tools, bare_in_work, separate_git_folder_in_tools):
            with self.subTest(case=make.__name__):
                scratch, outside = self.tmp / f"s-{make.__name__}", self.tmp / f"user-{make.__name__}"
                self.layout(scratch)
                make(scratch, outside)
                for key, value in (("user.name", "Test"), ("user.email", "test@example.com")):
                    self.git(outside, "config", key, value)
                (outside / "fix.txt").write_text("my fix")
                self.git(outside, "add", "fix.txt")
                self.git(outside, "commit", "-q", "-m", "my fix commit")
                before = self.tree()
                self.assertRefused(self.delete("--apply", scratch=scratch), "the git folder")
                self.assertEqual(self.tree(), before)
                self.assertEqual(self.git(outside, "log", "-1", "--format=%s"), "my fix commit")

    def test_folder_with_entries_that_a_run_does_not_make_is_refused(self):
        other = git_init(self.tmp / "other")
        bare = self.tmp / "bare.git"
        run(["git", "init", "-q", "--bare", bare], check=True)
        (self.scratch / "src").mkdir()
        for scratch, name in ((self.scratch, "src"), (self.repo, ".git"), (bare, "HEAD")):
            with self.subTest(name=name):
                before = self.tree()
                self.assertRefused(self.delete("--apply", scratch=scratch, repo=other),
                                   f"holds entries that a bug hunt does not make: {name}")
                self.assertEqual(self.tree(), before)

    def test_process_with_the_scratch_folder_and_its_start_time_stops(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", str(self.scratch)],
                                 cwd=self.scratch / "work")
        self.addCleanup(child.wait, 30)
        self.addCleanup(child.kill)
        records = REAL_PROCESS_SCAN()
        if records is None:
            tool_missing(self, "the process list command (PowerShell or ps) is not available")
        started = next(started for pid, _, started, _ in records if pid == child.pid)
        result = run([sys.executable, "-I", SCRIPT, "delete-temp", "--report-dir", self.report_dir,
                      "--scratch", self.scratch, "--repo", self.repo, "--pid", f"{child.pid}={started}", "--apply"],
                     timeout=180)
        self.assertResult(result, 0, f"DELETED: {self.scratch}")
        self.assertIn(f"STOPPED: pid={child.pid}", result.stdout.splitlines())
        self.assertIsNotNone(child.wait(30))

    def test_process_with_another_start_time_does_not_stop(self):
        record = (4242, 1, "Wed Oct 15 09:00:00 2026", f"python3 serve.py {self.scratch}")
        with mock.patch.object(cr, "list_processes", return_value=[record]), mock.patch.object(cr, "stop") as stop:
            code, lines = self.delete("--apply", "--pid", "4242=Wed Oct 15 09:30:00 2026")
        self.assertEqual(code, 0, lines)
        stop.assert_not_called()
        self.assertTrue(any(line.startswith("NOT STOPPED: pid=4242: it started at") for line in lines), lines)

    def test_matching_process_stops_only_with_apply(self):
        record = (4242, 1, "Sat Nov  1 09:00:00 2026", f"python3 serve.py {self.scratch / 'work'}")
        for extra, calls in (((), 0), (("--apply",), 1)):
            with self.subTest(extra=extra):
                with mock.patch.object(cr, "list_processes", return_value=[record]), \
                        mock.patch.object(cr, "stop") as stop:
                    code, lines = self.delete("--pid", "4242=Sat Nov 1 09:00:00 2026", *extra)
                self.assertEqual(code, 0, lines)
                self.assertEqual(stop.call_count, calls, lines)
                self.assertEqual("WOULD STOP: pid=4242" in lines, not extra, lines)

    def test_process_that_names_the_real_path_of_the_scratch_folder_stops(self):
        alias = self.tmp / "alias"
        self.link(alias, self.tmp, folder=True)
        started = "Wed Oct 15 09:00:00 2026"
        record = (4242, 1, started, f"python3 serve.py {os.path.realpath(self.scratch)}")
        with mock.patch.object(cr, "list_processes", return_value=[record]), mock.patch.object(cr, "stop") as stop:
            code, lines = self.delete("--apply", "--pid", f"4242={started}", scratch=alias / "scratch")
        self.assertEqual(code, 0, lines)
        stop.assert_called_once()

    def test_process_list_that_fails_stops_no_process(self):
        with mock.patch.object(cr, "list_processes", return_value=None), mock.patch.object(cr, "stop") as stop:
            code, lines = self.delete("--apply", "--pid", "4242=Wed Oct 15 09:00:00 2026")
        self.assertEqual(code, 0, lines)
        stop.assert_not_called()
        self.assertIn("NOT STOPPED: pid=4242: the script cannot list the processes", lines)

    @unittest.skipIf(os.name == "nt", "taskkill /F ends each process")
    def test_stop_waits_for_the_end_of_the_process_and_names_one_that_still_runs(self):
        handlers = {"ignores SIGTERM": "signal.SIG_IGN",
                    "ends late": "lambda number, frame: (time.sleep(0.5), sys.exit(0))"}
        for case, handler in handlers.items():
            with self.subTest(case=case):
                code_text = (f"import signal, sys, time; signal.signal(signal.SIGTERM, {handler}); "
                             "print('ready', flush=True); time.sleep(120)")
                child = subprocess.Popen([sys.executable, "-c", code_text, str(self.scratch)], stdout=subprocess.PIPE)
                self.addCleanup(child.wait, 30)
                self.addCleanup(child.kill)
                self.addCleanup(child.stdout.close)
                self.assertEqual(child.stdout.readline().strip(), b"ready")
                records = REAL_PROCESS_SCAN()
                if records is None:
                    tool_missing(self, "the process list command (ps) is not available")
                started = next(started for pid, _, started, _ in records if pid == child.pid)
                with mock.patch.object(cr, "list_processes", REAL_PROCESS_SCAN), \
                        mock.patch.object(cr, "STOP_SECONDS", 3):
                    code, lines = self.delete("--pid", f"{child.pid}={started}", "--apply")
                if case == "ends late":
                    self.assertIn(f"STOPPED: pid={child.pid}", lines)
                    self.assertIsNotNone(child.wait(30))
                else:
                    self.assertTrue(any(line.startswith(f"NOT STOPPED: pid={child.pid}: it still runs")
                                        for line in lines), lines)
                    self.assertNotIn(f"STOPPED: pid={child.pid}", lines)
                    self.assertIsNone(child.poll())
                self.layout(self.scratch)

    def test_process_that_does_not_name_the_scratch_folder_or_runs_the_script_does_not_stop(self):
        started = "Wed Oct 15 09:00:00 2026"
        cases = (([(4242, 1, started, "python3 serve.py /srv/app")], 4242, "does not name the scratch folder"),
                 ([(4242, 1, started, f"python3 serve.py {self.scratch}-old/x")], 4242,
                  "does not name the scratch folder"),
                 ([(os.getpid(), 1, started, f"python3 check_report.py {self.scratch}")], os.getpid(),
                  "runs this script"),
                 ([(os.getpid(), 9999, started, "python3 x"), (9999, 1, started, f"bash -c run {self.scratch}")], 9999,
                  "runs this script"))
        for records, pid, text in cases:
            with self.subTest(command=records[-1][3]):
                with mock.patch.object(cr, "list_processes", return_value=records), \
                        mock.patch.object(cr, "stop") as stop:
                    code, lines = self.delete("--pid", f"{pid}={started}")
                self.assertEqual(code, 0, lines)
                stop.assert_not_called()
                self.assertTrue(any(line.startswith("NOT STOPPED: ") and text in line for line in lines), lines)

    def test_missing_scratch_folder_gives_not_found_and_exit_0(self):
        shutil.rmtree(self.scratch)
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertIn(f"NOT FOUND: {self.scratch}", lines)

    def test_output_has_at_most_40_lines(self):
        for i in range(50):
            (self.report_dir / f"_bug-hunt-progress-area-{i:02d}.md").write_text("x")
        code, lines = self.delete()
        self.assertEqual(code, 0, lines)
        self.assertEqual(len(lines), 40, lines)
        self.assertEqual(lines[-1], "... 14 more lines")


class OutputTests(unittest.TestCase):
    def test_line_longer_than_the_limit_is_cut(self):
        out, buffer = cr.Output(), io.StringIO()
        out.add("ERROR: " + "x" * 5000)
        with contextlib.redirect_stdout(buffer):
            out.flush()
        self.assertLess(len(buffer.getvalue()), 400)
        self.assertTrue(buffer.getvalue().endswith("... 4707 more characters\n"), buffer.getvalue()[-60:])

    def test_mount_table_gives_field_5_with_its_escapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / "mountinfo"
            table.write_text("22 1 8:1 / / rw - ext4 /dev/sda rw\n"
                             "36 22 8:1 /src /srv/run/m\\040nt rw shared:1 - ext4 /dev/sda rw\n", encoding="utf-8")
            self.assertEqual(cr.mount_points(str(table)), ["/", "/srv/run/m nt"])

    def test_name_with_a_line_break_stays_on_one_line(self):
        self.assertEqual(cr.show("a\nb"), '"a\\nb"')
        self.assertEqual(cr.show("a b"), "a b")

    def test_git_that_gives_no_result_in_time_returns_code_124(self):
        with mock.patch.object(cr.subprocess, "run", side_effect=subprocess.TimeoutExpired(["git"], 7)):
            code, out, err = cr.git(".", "version", timeout=7)
        self.assertEqual((code, out), (124, ""))
        self.assertIn("7 seconds", err)


if __name__ == "__main__":
    unittest.main()
