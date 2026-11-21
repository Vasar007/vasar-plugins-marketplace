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
from testkit import ScratchCase, git_init, run

SCRIPT = REPO / "essentials/dev-essentials/skills/bug-hunt/scripts/check_report.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "bug-hunt"
cr = load_module("check_report", SCRIPT)
REAL_PROCESS_SCAN = cr.list_processes


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
        self.assertIn(f"SNAPSHOT: ref {self.scratch / 'snapshot-ref'} files=3 git=3", lines)
        self.assertIn("SNAPSHOT: base none (no base comparison)", lines)

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
        # A clone writes the line ends of core.autocrlf, as a checkout does.
        self.assertEqual((self.scratch / "snapshot-base" / "README.md").read_text(encoding="utf-8"), "# Release\n")

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
                (self.scratch / name / "old.txt").write_text("old")
                self.assertRefused(self.snapshot(sha), f"{name} exists and is not an empty folder")
                self.assertEqual(sorted(p.name for p in self.scratch.iterdir()), [name])
                shutil.rmtree(self.scratch)

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
        for name in ("snapshot-ref/README.md", "snapshot-base/README.md", "work/hunter-1/log.txt", "tools/x.txt",
                     "known-issues.md"):
            path = self.scratch / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")
        for name in self.KEPT + self.PROGRESS:
            path = self.report_dir / name
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

    def link(self, path, target, folder=False):
        try:
            Path(path).symlink_to(target, target_is_directory=folder)
        except OSError as error:
            self.skipTest(f"no right to make a link: {error}")

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

    def test_drive_root_is_refused(self):
        root = Path(self.tmp.anchor)
        self.assertRefused(self.delete(scratch=root), "is a drive root or a mount point")

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
        cases = ((linked / "scratch", self.repo, "the repository folder"),
                 (self.repo / "scratch", linked, "the repository folder"),
                 (bare / "scratch", bare, "the repository folder"))
        for scratch, repo, text in cases:
            with self.subTest(scratch=scratch.relative_to(self.tmp), repo=repo.name):
                shutil.copytree(self.scratch, scratch)
                before = self.tree()
                self.assertRefused(self.delete("--apply", scratch=scratch, repo=repo), text)
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
        code, lines = self.delete("--apply")
        self.assertEqual(code, 0, lines)
        self.assertFalse(self.scratch.exists())

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
        self.assertResult(result, 0, f"STOPPED: pid={child.pid}", f"DELETED: {self.scratch}")
        self.assertIsNotNone(child.wait(30))

    def test_process_with_another_start_time_does_not_stop(self):
        record = (4242, 1, "Wed Oct 15 09:00:00 2026", f"python3 serve.py {self.scratch}")
        with mock.patch.object(cr, "list_processes", return_value=[record]), mock.patch.object(cr, "stop") as stop:
            code, lines = self.delete("--apply", "--pid", "4242=Wed Oct 15 09:30:00 2026")
        self.assertEqual(code, 0, lines)
        stop.assert_not_called()
        self.assertTrue(any(line.startswith("NOT STOPPED: pid=4242: it started at") for line in lines), lines)

    def test_process_that_does_not_name_the_scratch_folder_or_runs_the_script_does_not_stop(self):
        started = "Wed Oct 15 09:00:00 2026"
        cases = (((4242, 1, started, "python3 serve.py /srv/app"), "does not name the scratch folder"),
                 ((os.getpid(), 1, started, f"python3 check_report.py {self.scratch}"), "runs this script"))
        for record, text in cases:
            with self.subTest(text=text):
                with mock.patch.object(cr, "list_processes", return_value=[record]), \
                        mock.patch.object(cr, "stop") as stop:
                    code, lines = self.delete("--pid", f"{record[0]}={started}")
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


if __name__ == "__main__":
    unittest.main()
