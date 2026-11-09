"""Tests for tests/evals/compare_versions.py.

The tests build result files from fixtures/result.json and call no model.
"""
import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from support import load_module, tool_missing

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "compare_versions.py"
cv = load_module("compare_versions", SCRIPT)
RESULT = json.loads((HERE / "fixtures" / "result.json").read_text(encoding="utf-8"))


def case(doc, name):
    return next(c for c in doc["cases"] if c["name"] == name)


def grader(run, name):
    return next(g for g in run["graders"] if g["name"] == name)


class CompareCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.base = copy.deepcopy(RESULT)
        self.head = copy.deepcopy(RESULT)

    def write(self, doc, name):
        path = self.tmp / name
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def run_main(self, *args):
        """Run main() with args. Return the exit code, stdout, and stderr."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cv.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def compare(self, *extra, base=None, head=None):
        base = base or [self.write(self.base, "base.json")]
        head = head or [self.write(self.head, "head.json")]
        return self.run_main("compare", "--base", *base, "--head", *head, *extra)

    def fail_run(self, doc, case_name, index, grader_name="fixed"):
        """Fail one grader of one run, and score the run again as claude plugin eval does."""
        run = case(doc, case_name)["arms"]["with"][index]
        grader(run, grader_name)["passed"] = False
        run["score"] = sum(g["weight"] for g in run["graders"] if g["passed"]) / sum(g["weight"] for g in run["graders"])


class VerdictTests(CompareCase):
    def test_same_results_hold(self):
        code, out, _ = self.compare("--fail-if-worse")
        self.assertEqual(code, 0, out)
        self.assertIn("head holds.", out)
        self.assertIn("| mean case score | 1.00 | 1.00 | +0.00 |", out)
        self.assertNotIn("## Cases that changed", out)

    def test_lower_mean_does_not_hold(self):
        for index in range(3):
            self.fail_run(self.head, "off-by-one", index)
        code, out, _ = self.compare()
        self.assertEqual(code, 0, out)
        self.assertIn("head scores lower than base, so the change does not hold.", out)
        self.assertIn("| off-by-one | 1.00 | 0.33 | 3/3 |", out)
        self.assertEqual(self.compare("--fail-if-worse")[0], 1)

    def test_case_with_no_scored_runs_at_head_gives_no_verdict(self):
        self.head["cases"] = [c for c in self.head["cases"] if c["name"] != "near-miss"]
        code, out, _ = self.compare("--fail-if-worse")
        self.assertEqual(code, 1, out)
        self.assertIn("No verdict yet. These cases have scored runs at base and none at head: near-miss.", out)

    def test_side_with_no_cases_has_no_model_list(self):
        self.head["cases"] = []
        out = self.compare()[1]
        self.assertIn("- The head has no results, so the agent model is not compared.", out)
        self.assertNotIn("head: )", out)

    def test_case_only_at_head_is_noted(self):
        self.base["cases"] = [c for c in self.base["cases"] if c["name"] != "near-miss"]
        code, out, _ = self.compare("--fail-if-worse")
        self.assertEqual(code, 0, out)
        self.assertIn("Not compared, because the base has no scored runs for them: near-miss.", out)

    def test_worse_case_with_held_mean_asks_for_the_traces(self):
        for index in range(3):
            self.fail_run(self.base, "off-by-one", index)
        for index in range(2):
            self.fail_run(self.head, "fires", index, "fires")
        code, out, _ = self.compare("--fail-if-worse")
        self.assertEqual(code, 0, out)
        self.assertIn("head scores the same or higher overall, but these cases got worse: fires.", out)

    def test_no_shared_case_is_an_input_error(self):
        self.base["cases"] = []
        self.head["cases"] = []
        code, _, err = self.compare()
        self.assertEqual(code, 2)
        self.assertIn("share no case with scored runs", err)


class ScoreTests(CompareCase):
    def test_run_score_is_the_score_of_the_tool_when_no_route_grader_exists(self):
        run = copy.deepcopy(case(RESULT, "fires")["arms"]["with"][0])
        run["score"] = 0.5
        self.assertEqual(cv.run_score(run), 0.5)
        run["graders"] = []
        self.assertIsNone(cv.run_score(run))

    def test_run_score_without_route_graders_uses_weights_and_skips_unscored_graders(self):
        run = copy.deepcopy(case(RESULT, "off-by-one")["arms"]["with"][0])
        self.assertEqual(cv.run_score(run), 1.0)
        grader(run, "no-push")["passed"] = False
        self.assertAlmostEqual(cv.run_score(run), 2 / 3)
        grader(run, "fixed")["scored"] = False
        self.assertEqual(cv.run_score(run), 0.0)
        grader(run, "route-agents")["passed"] = False
        self.assertEqual(cv.run_score(run), 0.0)
        run["graders"] = [grader(run, "route-agents")]
        self.assertIsNone(cv.run_score(run))

    def test_route_grader_change_is_information_only(self):
        for index in range(2):
            self.fail_run(self.head, "off-by-one", index, "route-agents")
        code, out, _ = self.compare("--fail-if-worse")
        self.assertEqual(code, 0, out)
        self.assertIn("head holds.", out)
        self.assertIn("## Route checks that changed", out)
        self.assertIn("| off-by-one | route-agents | 3/3 | 1/3 |", out)

    def test_run_with_an_error_keeps_its_score_and_is_counted(self):
        case(self.head, "near-miss")["arms"]["with"][0]["error"] = "timed out after 300s"
        code, out, _ = self.compare()
        self.assertEqual(code, 0, out)
        self.assertIn("| run errors | 0 | 1 | |", out)
        self.assertIn("| scored runs | 9 | 9 | |", out)
        self.assertIn("- head: near-miss: runs that ended with an error: 1, runs with no score: 0.", out)

    def test_run_with_no_grader_results_does_not_count(self):
        case(self.head, "near-miss")["arms"]["with"][0].update(error="exit 1: API Error", score=0, graders=[])
        out = self.compare()[1]
        self.assertIn("| scored runs | 9 | 8 | |", out)
        self.assertIn("head holds.", out)
        self.assertIn("- head: near-miss: runs that ended with an error: 1, runs with no score: 1.", out)

    def test_run_with_skipped_paid_graders_does_not_count(self):
        case(self.head, "fires")["arms"]["with"][0]["skippedPaidGraders"] = True
        out = self.compare()[1]
        self.assertIn("| scored runs | 9 | 8 | |", out)
        self.assertIn("- head: fires: runs that ended with an error: 0, runs with no score: 1.", out)


class NoiseTests(CompareCase):
    def test_change_of_one_run_is_listed_to_run_again(self):
        self.fail_run(self.head, "off-by-one", 0)
        code, out, _ = self.compare()
        self.assertIn("## Run again", out)
        self.assertIn("- off-by-one", out)

    def test_change_of_all_runs_is_not_listed(self):
        for index in range(3):
            self.fail_run(self.head, "off-by-one", index)
        self.assertNotIn("## Run again", self.compare()[1])

    def test_different_run_counts_are_listed_to_run_again(self):
        row = {"base_scores": [0.0, 0.0, 1.0, 1.0], "head_scores": [0.0, 1.0, 1.0]}
        self.assertEqual(cv.runs_that_differ(row), 1)

    def test_all_runs_that_drop_the_same_are_not_noise(self):
        for run in case(self.head, "fires")["arms"]["with"]:
            run["score"] = 0.75
        code, out, _ = self.compare()
        self.assertIn("| fires | 1.00 | 0.75 | 3/3 |", out)
        self.assertNotIn("## Run again", out)

    def test_change_of_one_run_with_a_lower_mean_is_noise(self):
        case(self.head, "fires")["arms"]["with"][0]["score"] = 0.25
        out = self.compare()[1]
        self.assertIn("## Run again", out)
        self.assertIn("- fires", out)

    def test_case_with_one_run_is_listed(self):
        for doc in (self.base, self.head):
            for c in doc["cases"]:
                c["arms"]["with"] = c["arms"]["with"][:1]
        self.fail_run(self.head, "off-by-one", 0)
        self.assertIn("- off-by-one", self.compare()[1])

    def test_extra_result_files_add_runs(self):
        extra = copy.deepcopy(self.head)
        self.fail_run(self.head, "off-by-one", 0)
        heads = [self.write(self.head, "head.json"), self.write(extra, "head-more.json")]
        code, out, _ = self.compare(head=heads)
        self.assertIn("Head files: head.json, head-more.json.", out)
        self.assertIn("| off-by-one | 1.00 | 0.89 | 3/6 |", out)


class NoteTests(CompareCase):
    def test_models_of_both_sides_are_named(self):
        out = self.compare()[1]
        self.assertIn("- Agent model on both sides: model-under-test-1.", out)
        self.assertIn("- Judge model on both sides: judge-model-1.", out)

    def test_different_models_give_a_warning(self):
        self.head["suite"]["modelOverride"] = "model-under-test-2"
        out = self.compare()[1]
        self.assertIn("The sides used different agent models (base: model-under-test-1, head: model-under-test-2).",
                      out)

    def test_missing_model_id_gives_a_warning(self):
        del self.base["suite"]["modelOverride"]
        del self.head["suite"]["judgeModel"]
        out = self.compare()[1]
        self.assertIn("The agent model is not recorded on one side (base: not recorded, "
                      "head: model-under-test-1). Pass a full model id with --model", out)
        self.assertIn("The judge model is not recorded on one side", out)

    def test_case_model_counts_when_no_override_is_set(self):
        for doc in (self.base, self.head):
            del doc["suite"]["modelOverride"]
            for c in doc["cases"]:
                c["model"] = "case-model-1"
        self.assertIn("- Agent model on both sides: case-model-1.", self.compare()[1])

    def test_partial_result_and_other_claude_version_are_noted(self):
        self.head["partial"] = True
        self.head["partialReason"] = "cost_ceiling"
        self.head["claudeVersion"] = "2.1.310"
        out = self.compare()[1]
        self.assertIn("head: the suite did not finish in head.json (cost_ceiling).", out)
        self.assertIn("The sides ran on different Claude Code versions (base: 2.1.309, head: 2.1.310).", out)

    def test_cost_and_duration_are_shown(self):
        self.head["costUsd"] = 0.9
        out = self.compare()[1]
        self.assertIn("| cost (USD) | 0.45 | 0.90 | +100% |", out)
        self.assertIn("| duration (s) | 360 | 360 | +0% |", out)

    def test_report_file(self):
        target = self.tmp / "report.md"
        code, out, _ = self.compare("--out", target)
        self.assertEqual(target.read_text(encoding="utf-8"), out)


class InputErrorTests(CompareCase):
    def test_wrong_schema_version(self):
        self.head["schemaVersion"] = 2
        code, _, err = self.compare()
        self.assertEqual(code, 2)
        self.assertIn("not a claude plugin eval result with schemaVersion 1", err)

    def test_file_that_is_not_json(self):
        bad = self.tmp / "bad.json"
        bad.write_text("{", encoding="utf-8")
        code, _, err = self.compare(head=[bad])
        self.assertEqual(code, 2)
        self.assertIn("cannot read the result file", err)


class RunTests(CompareCase):
    """The run subcommand with a real git repository and a stand-in for claude plugin eval."""

    def setUp(self):
        super().setUp()
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.repo = self.tmp / "repo"
        plugin = self.repo / "group" / "demo"
        (plugin / ".claude-plugin").mkdir(parents=True)
        (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "demo", "version": "1.0.0"}\n')
        (plugin / "skills" / "demo").mkdir(parents=True)
        (plugin / "skills" / "demo" / "SKILL.md").write_text("old skill\n")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.base_sha = self.git("rev-parse", "HEAD").strip()
        (plugin / "skills" / "demo" / "SKILL.md").write_text("new skill\n")
        (plugin / "evals" / "triggers" / "fires").mkdir(parents=True)
        (plugin / "evals" / "triggers" / "fires" / "prompt.md").write_text("Do the demo task.\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "head")
        self.calls = []

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.com",
                               *args], capture_output=True, text=True, check=True).stdout

    def fake_eval(self, command, cwd):
        """Stand-in for claude plugin eval: record the call, and write the fixture as the result."""
        plugin = Path(command[3])
        self.calls.append({"command": command, "cwd": cwd,
                           "skill": (plugin / "skills" / "demo" / "SKILL.md").read_text(),
                           "has_case": (plugin / "evals" / "triggers" / "fires" / "prompt.md").is_file()})
        Path(command[command.index("--json") + 1]).write_text(json.dumps(RESULT), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def run_main(self, *args, runner=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cv.main([str(a) for a in args], runner=runner or self.fake_eval)
        return code, out.getvalue(), err.getvalue()

    def run_args(self, *extra, base=None, head="HEAD"):
        return ("run", "--repo", self.repo, "--plugin", "group/demo", "--base", base or self.base_sha, "--head", head,
                "--model", "model-under-test-1", "--judge-model", "judge-model-1", "--out", self.tmp / "out",
                "--claude", sys.executable, *extra)

    def eval_in_its_own_folder(self, command, cwd):
        """Stand-in that writes the result relative to its own folder, as the real child process does."""
        self.calls.append({"command": command, "cwd": cwd})
        (Path(cwd) / command[command.index("--json") + 1]).write_text(json.dumps(RESULT), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def eval_with_one_worse_run(self, command, cwd):
        """Stand-in that gives the head one failed run, so the report asks for more runs."""
        doc = copy.deepcopy(RESULT)
        if Path(command[3]).parts[-3] == "head":
            self.fail_run(doc, "off-by-one", 0)
        Path(command[command.index("--json") + 1]).write_text(json.dumps(doc), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def test_both_sides_run_the_cases_of_the_head(self):
        code, out, err = self.run_main(*self.run_args())
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["skill"] for c in self.calls], ["old skill\n", "new skill\n"])
        self.assertTrue(all(c["has_case"] for c in self.calls))
        self.assertIn(f"# Eval comparison: base {self.base_sha[:12]} and head", out)
        self.assertEqual((self.tmp / "out" / "report.md").read_text(encoding="utf-8"), out)
        self.assertTrue((self.tmp / "out" / "base.json").is_file())

    def test_eval_command_pins_the_models_and_puts_lists_last(self):
        self.run_main(*self.run_args("--tag", "smoke", "triggers", "--allow-tools", "Write", "--case", "fires*",
                                     "--max-cost-usd", "5", "--concurrency", "3"))
        command = self.calls[0]["command"]
        self.assertEqual(command[1:3], ["plugin", "eval"])
        for flag, value in (("--model", "model-under-test-1"), ("--judge-model", "judge-model-1"),
                            ("--ablation", "none"), ("--threshold", "0"), ("--runs", "3"), ("--case", "fires*"),
                            ("--max-cost-usd", "5.0"), ("--concurrency", "3")):
            self.assertEqual(command[command.index(flag) + 1], value, flag)
        self.assertIn("--trust-plugin", command)
        self.assertIn("--no-publish", command)
        self.assertEqual(command[-5:], ["--tag", "smoke", "triggers", "--allow-tools", "Write"])

    def test_concurrency_is_left_out_by_default(self):
        self.run_main(*self.run_args())
        self.assertNotIn("--concurrency", self.calls[0]["command"])

    def test_relative_out_folder_gets_the_results(self):
        old = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, old)
        code, out, err = self.run_main(*self.run_args("--out", "relative-out"), runner=self.eval_in_its_own_folder)
        self.assertEqual(code, 0, err)
        self.assertTrue((self.tmp / "relative-out" / "base.json").is_file())
        self.assertTrue((self.tmp / "relative-out" / "report.md").is_file())

    def test_existing_result_in_the_out_folder_is_not_overwritten(self):
        (self.tmp / "out").mkdir()
        (self.tmp / "out" / "head.json").write_text("old result", encoding="utf-8")
        code, _, err = self.run_main(*self.run_args())
        self.assertEqual(code, 2)
        self.assertIn("head.json already exists", err)
        self.assertEqual(self.calls, [])
        self.assertEqual((self.tmp / "out" / "head.json").read_text(encoding="utf-8"), "old result")

    def test_report_gives_the_commands_to_run_unclear_cases_again(self):
        code, out, err = self.run_main(*self.run_args("--tag", "smoke"), runner=self.eval_with_one_worse_run)
        self.assertEqual(code, 0, err)
        folder = (self.tmp / "out").resolve().as_posix()
        self.assertIn("- off-by-one", out)
        self.assertRegex(out, r"run --plugin group/demo --base " + self.base_sha + r" --head [0-9a-f]{40} "
                              r"--model model-under-test-1 --judge-model judge-model-1 --case off-by-one --runs 4 "
                              r"--out \S+out-more-1 .*--claude \S+ --tag smoke")
        self.assertIn(f"compare --base {folder}/base.json {folder}-more-1/base.json "
                      f"--head {folder}/head.json {folder}-more-1/head.json", out)

    def test_report_repeats_the_concurrency(self):
        code, out, err = self.run_main(*self.run_args("--concurrency", "2", "--tag", "smoke"),
                                       runner=self.eval_with_one_worse_run)
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"--case off-by-one --runs 4 --out \S+out-more-1 .*--concurrency 2 --tag smoke")

    def baseline_args(self, *extra):
        return ("baseline", "--repo", self.repo, "--plugin", "group/demo", "--commit", "HEAD",
                "--model", "model-under-test-1", "--judge-model", "judge-model-1", "--out", self.tmp / "out",
                "--claude", sys.executable, *extra)

    def main_on(self, platform, folder, arguments):
        """Run main() as if the platform and the temp folder were these values."""
        with (
            mock.patch.object(cv, "is_linux", return_value=platform == "linux"),
            mock.patch.object(cv, "temp_folder", return_value=folder),
        ):
            return self.run_main(*arguments)

    def test_bash_grant_with_the_temp_folder_under_tmp_stops_before_any_run(self):
        folders = ("/tmp", "/tmp/", "/tmp/eval-runs", "/tmp/a/../b", "/var/tmp", "/var/tmp/x", "/dev/shm", "/dev/shm/x",
                   "/run/shm", "/run/shm/x")
        for folder in folders:
            for arguments in (self.run_args("--allow-tools", "Bash", "Write"),
                              self.baseline_args("--allow-tools", "Write", "Bash")):
                with self.subTest(folder=folder, command=arguments[0]):
                    code, _, err = self.main_on("linux", folder, arguments)
                    self.assertEqual(code, 2)
                    self.assertRegex(err, r"the eval sandbox denies writes to (?:/tmp|/var/tmp|/dev/shm|/run/shm),")
                    self.assertIn("Set TMPDIR to a folder in your home", err)
                    self.assertEqual(self.calls, [])
                    self.assertFalse((self.tmp / "out").exists())

    def test_temp_folder_outside_tmp_or_no_bash_grant_or_other_platform_is_allowed(self):
        cases = (("linux", "/home/user/.cache/plugin-evals/tmp", ("--allow-tools", "Bash")),
                 ("linux", "/tmpfiles", ("--allow-tools", "Bash")),
                 ("linux", "/var/tmpfiles", ("--allow-tools", "Bash")),
                 ("linux", "/run/shmem", ("--allow-tools", "Bash")),
                 ("linux", "/tmp", ("--allow-tools", "Write", "Edit")),
                 ("linux", "/tmp", ()),
                 ("win32", "/tmp", ("--allow-tools", "Bash")))
        for platform, folder, extra in cases:
            with self.subTest(platform=platform, folder=folder, extra=extra):
                shutil.rmtree(self.tmp / "out", ignore_errors=True)
                self.calls = []
                code, out, err = self.main_on(platform, folder, self.baseline_args(*extra))
                self.assertEqual(code, 0, out + err)
                self.assertEqual(len(self.calls), 1)

    def test_temp_folder_follows_tmpdir(self):
        with mock.patch.dict(os.environ, {"TMPDIR": str(self.tmp)}), mock.patch.object(tempfile, "tempdir", None):
            self.assertEqual(Path(cv.temp_folder()), self.tmp.resolve())

    @unittest.skipUnless(sys.platform.startswith("linux"), "needs a Linux symbolic link")
    def test_temp_folder_resolves_a_link_into_tmp(self):
        target = Path(tempfile.mkdtemp(dir="/tmp"))
        self.addCleanup(shutil.rmtree, target, ignore_errors=True)
        link = self.tmp / "link"
        link.symlink_to(target)
        with mock.patch.dict(os.environ, {"TMPDIR": str(link)}), mock.patch.object(tempfile, "tempdir", None):
            code, _, err = self.run_main(*self.run_args("--allow-tools", "Bash"))
        self.assertEqual(code, 2)
        self.assertIn("denies writes to /tmp", err)

    def test_claude_command_that_is_not_found_is_an_input_error(self):
        code, _, err = self.run_main(*self.run_args("--claude", "no-such-claude-command"))
        self.assertEqual(code, 2)
        self.assertIn("cannot find the command no-such-claude-command", err)
        self.assertEqual(self.calls, [])

    def test_eval_folder_comes_from_the_manifest(self):
        manifest = self.repo / "group" / "demo" / ".claude-plugin" / "plugin.json"
        manifest.write_text('{"name": "demo", "version": "1.0.0", "experimental": {"evals": "checks"}}\n')
        (self.repo / "group" / "demo" / "evals").rename(self.repo / "group" / "demo" / "checks")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "manifest")
        code, out, err = self.run_main(*self.run_args())
        self.assertEqual(code, 0, err)
        command = self.calls[0]["command"]
        self.assertEqual(command[command.index("--eval-dir") + 1], "checks")

    def test_manifest_folder_outside_the_plugin_falls_back_to_evals(self):
        for value in ("../outside", "/abs/evals"):
            with self.subTest(value=value):
                folder = Path(self.tmp) / "plugin"
                (folder / ".claude-plugin").mkdir(parents=True, exist_ok=True)
                (folder / ".claude-plugin" / "plugin.json").write_text(json.dumps({"experimental": {"evals": value}}))
                self.assertIsNone(cv.manifest_suite(folder))

    def test_missing_result_is_an_input_error(self):
        code, _, err = self.run_main(*self.run_args(), runner=lambda command, cwd: SimpleNamespace(returncode=1))
        self.assertEqual(code, 2)
        self.assertIn("claude plugin eval exited with 1 and wrote no result for the base commit", err)

    def test_suite_missing_at_head_is_an_input_error(self):
        code, _, err = self.run_main(*self.run_args(head=self.base_sha))
        self.assertEqual(code, 2)
        self.assertIn("group/demo/evals does not exist at the head commit", err)

    def test_unknown_commit_is_an_input_error(self):
        code, _, err = self.run_main(*self.run_args(base="no-such-branch"))
        self.assertEqual(code, 2)
        self.assertIn("git rev-parse", err)


class DependencyTests(CompareCase):
    """The plugin copy of a run holds the plugins that the manifest lists in dependencies."""

    git = RunTests.git
    run_main = RunTests.run_main
    run_args = RunTests.run_args
    eval_with_one_worse_run = RunTests.eval_with_one_worse_run

    def setUp(self):
        super().setUp()
        if shutil.which("git") is None:
            tool_missing(self, "git not found")
        self.repo = self.tmp / "repo"
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest(["helper"]))
        self.write_file("group/demo/skills/demo/SKILL.md", "demo skill\n")
        self.write_file("tools/helper/.claude-plugin/plugin.json", '{"name": "helper", "version": "1.0.0"}\n')
        self.write_file("tools/helper/skills/helper/SKILL.md", "old helper\n")
        self.write_file(".claude-plugin/marketplace.json", json.dumps({
            "name": "test-market",
            "plugins": [{"name": "demo", "source": "./group/demo"}, {"name": "helper", "source": "./tools/helper"}],
        }))
        self.git("init", "-q")
        self.commit("base")
        self.base_sha = self.git("rev-parse", "HEAD").strip()
        self.write_file("tools/helper/skills/helper/SKILL.md", "new helper\n")
        self.write_file("group/demo/evals/triggers/fires/prompt.md", "Do the demo task.\n")
        self.commit("head")
        self.calls = []

    @staticmethod
    def manifest(dependencies):
        return json.dumps({"name": "demo", "version": "1.0.0", "dependencies": dependencies})

    def write_file(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def fake_eval(self, command, cwd):
        """Stand-in for claude plugin eval: record the dependency copy that the plugin folder holds."""
        plugin = Path(command[3])
        copy_of_helper = plugin / ".deps" / "helper" / "skills" / "helper" / "SKILL.md"
        stub_manifest = plugin / "eval-stubs" / "github" / ".claude-plugin" / "plugin.json"
        self.calls.append({"command": command, "helper": copy_of_helper.read_text() if copy_of_helper.is_file() else None,
                           "deps": sorted(p.name for p in (plugin / ".deps").glob("*")),
                           "stubs": sorted(p.name for p in (plugin / "eval-stubs").glob("*")),
                           "stub": stub_manifest.read_text() if stub_manifest.is_file() else None})
        Path(command[command.index("--json") + 1]).write_text(json.dumps(RESULT), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def baseline_args(self, *extra, commit="HEAD"):
        return ("baseline", "--repo", self.repo, "--plugin", "group/demo", "--commit", commit,
                "--model", "model-under-test-1", "--judge-model", "judge-model-1", "--out", self.tmp / "out",
                "--claude", sys.executable, *extra)

    def test_copy_holds_the_dependency_of_its_own_commit(self):
        code, out, err = self.run_main(*self.run_args())
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["helper"] for c in self.calls], ["old helper\n", "new helper\n"])

    def test_dependency_can_be_an_object_or_name_with_marketplace(self):
        for entry in ({"name": "helper", "version": "^1.0", "marketplace": "test-market"}, "helper@test-market"):
            with self.subTest(entry=entry):
                self.calls = []
                self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([entry, "helper"]))
                self.commit("entry")
                shutil.rmtree(self.tmp / "out", ignore_errors=True)
                code, out, err = self.run_main(*self.run_args())
                self.assertEqual(code, 0, out + err)
                self.assertEqual([c["deps"] for c in self.calls], [["helper"], ["helper"]])

    def test_plugin_without_dependencies_gets_no_deps_folder(self):
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([]))
        self.commit("no dependencies")
        code, out, err = self.run_main(*self.run_args(base="HEAD"))
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["deps"] for c in self.calls], [[], []])

    def test_dependency_that_is_not_in_the_marketplace_is_an_input_error(self):
        for entry in ("no-such-plugin", {"name": "helper", "marketplace": "other-market"}, "helper@other-market", 7):
            with self.subTest(entry=entry):
                self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([entry]))
                self.commit("bad entry")
                code, _, err = self.run_main(*self.run_args())
                self.assertEqual(code, 2)
                self.assertRegex(err, r"ERROR: (cannot read the dependency|the dependency)")
                self.assertEqual(self.calls, [])
                shutil.rmtree(self.tmp / "out", ignore_errors=True)

    def test_dependency_name_with_a_path_is_an_input_error(self):
        for name in ("../evil", "a/b", "..", ".hidden", "a\\b"):
            with self.subTest(name=name):
                self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([name]))
                self.commit("path entry")
                code, _, err = self.run_main(*self.run_args())
                self.assertEqual(code, 2)
                self.assertIn("is not a plugin name", err)
                self.assertEqual(self.calls, [])
                self.assertFalse((self.tmp / "evil").exists())
                shutil.rmtree(self.tmp / "out", ignore_errors=True)

    def args_with_plugin(self, arguments, plugin):
        """The arguments with another --plugin value."""
        arguments = list(arguments)
        arguments[arguments.index("--plugin") + 1] = plugin
        return arguments

    def test_plugin_path_outside_the_export_is_an_input_error(self):
        self.write_file("tests/evals/stubs/github/.claude-plugin/plugin.json", '{"name": "github"}\n')
        self.commit("stub")
        self.write_file("group/demo/eval-stubs/mine/note.txt", "not committed\n")
        real = self.repo / "group" / "demo"
        exports = self.tmp / "exports"
        exports.mkdir()
        # The export root is <exports>/compare-versions-<random>/<side>, so three steps up reach self.tmp.
        paths = (real.resolve().as_posix(), "../../../repo/group/demo")
        for plugin in paths:
            for arguments in (self.baseline_args(), self.run_args()):
                with self.subTest(plugin=plugin, command=arguments[0]):
                    shutil.rmtree(self.tmp / "out", ignore_errors=True)
                    self.calls = []
                    with mock.patch.object(tempfile, "tempdir", str(exports)):
                        code, _, err = self.run_main(*self.args_with_plugin(arguments, plugin))
                    self.assertEqual(code, 2)
                    self.assertIn("is not inside the repository", err)
                    self.assertEqual(self.calls, [])
                    self.assertFalse((real / ".deps").exists())
                    self.assertEqual(sorted(p.name for p in (real / "eval-stubs").iterdir()), ["mine"])

    @unittest.skipUnless(sys.platform.startswith("linux"), "needs a Linux symbolic link")
    def test_plugin_path_with_a_link_or_dots_inside_the_export_is_allowed(self):
        (self.repo / "group" / "alias").symlink_to("demo")
        self.commit("link")
        for plugin in ("group/alias", "group/../group/demo"):
            with self.subTest(plugin=plugin):
                shutil.rmtree(self.tmp / "out", ignore_errors=True)
                self.calls = []
                code, out, err = self.run_main(*self.args_with_plugin(self.baseline_args(), plugin))
                self.assertEqual(code, 0, out + err)
                self.assertEqual([c["helper"] for c in self.calls], ["new helper\n"])

    def test_baseline_writes_one_file_from_one_commit(self):
        head_sha = self.git("rev-parse", "HEAD").strip()
        code, out, err = self.run_main(*self.baseline_args(commit=head_sha))
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["helper"] for c in self.calls], ["new helper\n"])
        self.assertEqual(sorted(p.name for p in (self.tmp / "out").glob("*.json")), ["baseline.json"])
        self.assertIn(f"at {head_sha[:12]}", out)

    def test_stubs_are_copied_into_the_plugin_copy(self):
        self.write_file("tests/evals/stubs/github/.claude-plugin/plugin.json", '{"name": "github"}\n')
        self.commit("stub")
        code, out, err = self.run_main(*self.baseline_args())
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["stubs"] for c in self.calls], [["github"]])

    def test_both_sides_of_a_run_get_the_stubs_of_the_head(self):
        self.write_file("group/demo/eval-stubs/github/.claude-plugin/plugin.json", "old")
        self.commit("old stub in the plugin")
        base = self.git("rev-parse", "HEAD").strip()
        self.git("rm", "-rq", "group/demo/eval-stubs")
        self.write_file("tests/evals/stubs/github/.claude-plugin/plugin.json", "new")
        self.commit("stub moves out")
        code, out, err = self.run_main(*self.run_args(base=base))
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["stub"] for c in self.calls], ["new", "new"])

    def test_baseline_at_a_commit_without_the_stub_folder_keeps_the_stub_of_its_plugin(self):
        self.write_file("group/demo/eval-stubs/github/.claude-plugin/plugin.json", "old")
        self.commit("old stub in the plugin")
        code, out, err = self.run_main(*self.baseline_args())
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["stub"] for c in self.calls], ["old"])

    def test_a_run_with_an_old_head_gives_the_base_the_stub_of_the_head(self):
        self.write_file("tests/evals/stubs/github/.claude-plugin/plugin.json", "new")
        self.commit("stub moves out")
        base = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "-b", "old", self.base_sha)
        self.write_file("group/demo/evals/triggers/fires/prompt.md", "Do the demo task.\n")
        self.write_file("group/demo/eval-stubs/github/.claude-plugin/plugin.json", "old")
        self.commit("head with the old layout")
        code, out, err = self.run_main(*self.run_args(base=base))
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["stub"] for c in self.calls], ["old", "old"])

    def test_copy_of_the_dependency_has_no_eval_cases(self):
        self.write_file("tools/helper/evals/triggers/helper-fires/prompt.md", "Do the helper task.\n")
        self.commit("helper cases")
        seen = []

        def look(command, cwd):
            seen.append((Path(command[3]) / ".deps" / "helper" / "evals").exists())
            return self.fake_eval(command, cwd)
        code, out, err = self.run_main(*self.baseline_args(), runner=look)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(seen, [False])

    def test_base_without_the_dependency_of_the_head_is_an_input_error(self):
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([]))
        self.commit("drop the dependency")
        old_sha = self.git("rev-parse", "HEAD").strip()
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest(["helper"]))
        self.commit("declare it again")
        code, _, err = self.run_main(*self.run_args(base=old_sha))
        self.assertEqual(code, 2)
        self.assertIn("the head suite needs the dependency helper", err)
        self.assertEqual(self.calls, [])

    def test_extra_dependency_is_copied_without_being_declared(self):
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([]))
        self.commit("no dependencies")
        code, out, err = self.run_main(*self.baseline_args("--extra-dep", "helper"))
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["deps"] for c in self.calls], [["helper"]])
        self.assertEqual([c["helper"] for c in self.calls], ["new helper\n"])

    def test_extra_dependency_has_no_eval_cases_and_is_copied_once(self):
        self.write_file("tools/helper/evals/triggers/helper-fires/prompt.md", "Do the helper task.\n")
        self.commit("helper cases")
        seen = []

        def look(command, cwd):
            seen.append((Path(command[3]) / ".deps" / "helper" / "evals").exists())
            return self.fake_eval(command, cwd)
        code, out, err = self.run_main(*self.baseline_args("--extra-dep", "helper", "--extra-dep", "helper"), runner=look)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(seen, [False])
        self.assertEqual([c["deps"] for c in self.calls], [["helper"]])

    def test_extra_dependency_applies_to_both_sides_of_a_run(self):
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([]))
        self.commit("no dependencies")
        code, out, err = self.run_main(*self.run_args("--extra-dep", "helper", base="HEAD"))
        self.assertEqual(code, 0, out + err)
        self.assertEqual([c["deps"] for c in self.calls], [["helper"], ["helper"]])

    def test_report_repeats_the_extra_dependency_in_the_rerun_command(self):
        self.write_file("group/demo/.claude-plugin/plugin.json", self.manifest([]))
        self.commit("no dependencies")
        code, out, err = self.run_main(*self.run_args("--extra-dep", "helper", "--tag", "smoke", base="HEAD"),
                                       runner=self.eval_with_one_worse_run)
        self.assertEqual(code, 0, out + err)
        self.assertRegex(out, r"--case off-by-one --runs 4 --out \S+out-more-1 .*--extra-dep helper --tag smoke")

    def test_extra_dependency_that_is_not_in_the_marketplace_is_an_input_error(self):
        for name in ("no-such-plugin", "../evil"):
            with self.subTest(name=name):
                code, _, err = self.run_main(*self.baseline_args("--extra-dep", name))
                self.assertEqual(code, 2)
                self.assertRegex(err, r"ERROR: the dependency")
                self.assertEqual(self.calls, [])
                shutil.rmtree(self.tmp / "out", ignore_errors=True)

    def test_baseline_passes_the_ablation_and_keeps_the_temporary_folders_on_request(self):
        self.run_main(*self.baseline_args())
        command = self.calls[0]["command"]
        self.assertEqual(command[command.index("--ablation") + 1], "none")
        self.assertNotIn("--keep-temp", command)
        shutil.rmtree(self.tmp / "out", ignore_errors=True)
        self.run_main(*self.baseline_args("--ablation", "with-without", "--keep-temp"))
        command = self.calls[1]["command"]
        self.assertEqual(command[command.index("--ablation") + 1], "with-without")
        self.assertIn("--keep-temp", command)

    def test_baseline_with_an_unknown_ablation_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.run_main(*self.baseline_args("--ablation", "all"))

    def test_baseline_with_a_failed_eval_is_an_input_error(self):
        def failed_eval(command, cwd):
            Path(command[command.index("--json") + 1]).write_text(json.dumps({**RESULT, "cases": []}), encoding="utf-8")
            return SimpleNamespace(returncode=1)
        code, out, err = self.run_main(*self.baseline_args(), runner=failed_eval)
        self.assertEqual(code, 2)
        self.assertIn("claude plugin eval exited with 1 and wrote 0 case(s)", err)
        self.assertNotIn("Wrote the baseline", out)

    def test_baseline_does_not_overwrite_a_result(self):
        (self.tmp / "out").mkdir()
        (self.tmp / "out" / "baseline.json").write_text("old result", encoding="utf-8")
        code, _, err = self.run_main(*self.baseline_args())
        self.assertEqual(code, 2)
        self.assertIn("baseline.json already exists", err)
        self.assertEqual(self.calls, [])
        self.assertEqual((self.tmp / "out" / "baseline.json").read_text(encoding="utf-8"), "old result")

    def test_baseline_without_the_suite_is_an_input_error(self):
        code, _, err = self.run_main(*self.baseline_args(commit=self.base_sha))
        self.assertEqual(code, 2)
        self.assertIn("group/demo/evals does not exist at the baseline commit", err)
        self.assertEqual(self.calls, [])

class CommandLineTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", timeout=60)

    def test_compare_of_the_fixture_with_itself(self):
        fixture = HERE / "fixtures" / "result.json"
        result = self.run_script("compare", "--base", fixture, "--head", fixture, "--fail-if-worse")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("## Verdict", result.stdout)

    def test_usage_error_exits_with_2(self):
        self.assertEqual(self.run_script().returncode, 2)
        self.assertEqual(self.run_script("run", "--plugin", "x").returncode, 2)

    def test_concurrency_above_8_exits_with_2(self):
        result = self.run_script("baseline", "--plugin", "x", "--model", "m", "--judge-model", "j", "--out", "o",
                                 "--concurrency", "9")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
