"""Tests for tools/eval_results.py.

The tests read the result file and the trace of tests/evals/fixtures/, and small files that each test
writes into a temporary folder. They run the script as a child process and call no model.
"""
import json
import sys
import unittest

from support import REPO
from testkit import ScratchCase, run

SCRIPT = REPO / "tools" / "eval_results.py"
RESULT = REPO / "tests" / "evals" / "fixtures" / "result.json"
TRACE = REPO / "tests" / "evals" / "fixtures" / "replay-run" / "out" / "trace.jsonl"


def result_file(cost, runs):
    """A baseline.json with one case. Each run is (arm, score, folder, failed grader name or None)."""
    arms = {}
    for arm, score, folder, failed in runs:
        graders = [{"name": "kept", "passed": True}]
        if failed:
            graders.append({"name": failed, "passed": False, "score": 0})
        arms.setdefault(arm, []).append({
            "score": score, "costUsd": 0.5, "durationSeconds": 30, "error": None, "graders": graders,
            "tracePath": f"/home/user/.cache/plugin-evals/tmp/claude-eval-{folder}/out/trace.jsonl" if folder else None})
    return {"claudeVersion": "2.1.0", "costUsd": cost, "durationSeconds": 90,
            "aggregates": {"overallScore": 0.5, "overallPassRate": 0.5},
            "cases": [{"name": "case-a", "aggregates": {"score": 0.5}, "arms": arms}]}


class EvalResultsCase(ScratchCase):
    def tool(self, *args, code=0):
        result = run([sys.executable, "-I", SCRIPT, *args])
        self.assertResult(result, code)
        return result.stdout

    def write_json(self, name, data):
        path = self.tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path


class RunsTests(EvalResultsCase):
    def test_one_line_for_each_run_with_the_failed_graders(self):
        path = self.write_json("b.json", result_file(1.25, [("with", 1.0, "AbCd", None), ("with", 0.0, "EfGh", "route-x")]))
        out = self.tool("runs", path)
        self.assertIn("claude 2.1.0 cost 1.25 time 90 s score 0.5000 pass 0.5000", out)
        self.assertIn("-- case-a score 0.5", out)
        self.assertIn("   with score=1.0 cost=0.5 dur=30 folder=AbCd failed=[] err=None", out)
        self.assertIn("folder=EfGh failed=['route-x:0']", out)

    def test_reads_the_result_fixture_of_the_repository(self):
        out = self.tool("runs", RESULT)
        self.assertIn("claude 2.1.309 cost 0.45", out)
        self.assertEqual(out.count("   with score="), 9)

    def test_missing_file_fails_with_code_2(self):
        result = run([sys.executable, "-I", SCRIPT, "runs", self.tmp / "none.json"])
        self.assertResult(result, 2, "ERROR cannot read")


class SpendTests(EvalResultsCase):
    def test_sum_under_the_cap_passes(self):
        a = self.write_json("a/baseline.json", result_file(2.0, []))
        b = self.write_json("b/baseline.json", result_file(3.5, []))
        out = self.tool("spend", "--cap", "10", "--rest", "4", a, b)
        self.assertIn("spent 5.50 USD, rest 4.00 USD, sum 9.50 USD, cap 10.00 USD", out)

    def test_sum_over_the_cap_fails_with_code_3(self):
        a = self.write_json("a/baseline.json", result_file(8.0, []))
        out = self.tool("spend", "--cap", "10", "--rest", "2.5", a, code=3)
        self.assertIn("OVER THE CAP", out)

    def test_a_recording_counts_its_highest_turn(self):
        one = self.write_json("rec/turn-1.json", {"total_cost_usd": 1.0})
        two = self.write_json("rec/turn-2.json", {"total_cost_usd": 3.0})
        other = self.write_json("rec2/turn-1.json", {"total_cost_usd": 0.5})
        out = self.tool("spend", "--cap", "10", one, two, other)
        self.assertIn("spent 3.50 USD", out)

    def test_file_with_no_cost_fails_with_code_2(self):
        path = self.write_json("x.json", {"name": "x"})
        self.assertResult(run([sys.executable, "-I", SCRIPT, "spend", "--cap", "1", path]), 2, "no costUsd")


class KeptTests(EvalResultsCase):
    def test_each_kept_folder_once_in_order(self):
        path = self.write_json("b.json", result_file(1, [("with", 1, "B2", None), ("with", 1, "A1", None),
                                                         ("with", 1, "B2", None), ("with", 1, None, None)]))
        self.assertEqual(self.tool("kept", path), "- claude-eval-B2\n- claude-eval-A1\n")


class TraceTests(EvalResultsCase):
    def test_calls_of_the_main_session_and_of_a_subagent(self):
        out = self.tool("trace", TRACE)
        self.assertIn("[assistant] TEXT I read the issue first.", out)
        self.assertIn("[assistant] CALL mcp__plugin_github_github__issue_read", out)
        self.assertIn("[assistant sub] CALL mcp__plugin_github_github__issue_write", out)
        self.assertIn("[line 16] NOT JSON, skipped", out)

    def test_limit_and_max_lines_cut_the_output(self):
        out = self.tool("trace", TRACE, "--limit", "10", "--max-lines", "2")
        lines = out.splitlines()
        self.assertEqual(len(lines), 3, out)
        self.assertIn("more characters", lines[1])
        self.assertRegex(lines[2], r"^\.\.\. \d+ more lines\. Raise --max-lines to see them$")

    def test_text_outside_ascii_prints(self):
        path = self.tmp / "trace.jsonl"
        event = {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "a — b 中"}]}}
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        self.assertIn("[assistant] TEXT a", self.tool("trace", path))

    def test_zero_max_lines_is_a_usage_error(self):
        self.assertResult(run([sys.executable, "-I", SCRIPT, "trace", TRACE, "--max-lines", "0"]), 2)


if __name__ == "__main__":
    unittest.main()
