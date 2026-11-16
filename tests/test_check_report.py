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
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from support import REPO, load_module, tool_missing
from testkit import ScratchCase, run

SCRIPT = REPO / "essentials/dev-essentials/skills/bug-hunt/scripts/check_report.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bug-hunt"
cr = load_module("check_report", SCRIPT)


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def edit(text, old, new):
    """Replace the first old with new. Fail if the text has no old."""
    if old not in text:
        raise AssertionError(f"the fixture has no {old!r}")
    return text.replace(old, new, 1)


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
        self.assertPasses(self.check_text(text))


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


if __name__ == "__main__":
    unittest.main()
