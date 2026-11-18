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


def event(content, role="assistant", **more):
    return dict({"type": role, "message": {"role": role, "content": content}}, **more)


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

    def test_partial_file_and_case_with_no_run_are_named(self):
        data = result_file(1.0, [("with", 1.0, "AbCd", None)])
        data.update(partial=True, partialReason="cost_ceiling")
        data["cases"].append({"name": "case-b", "aggregates": {"score": None}, "arms": {"with": []}})
        out = self.tool("runs", self.write_json("b.json", data))
        self.assertIn("PARTIAL the suite did not finish: cost_ceiling\n-- case-a score 0.5\n", out)
        self.assertIn("-- case-b score None NO RUN\n", out)


class SpendTests(EvalResultsCase):
    def spend(self, *args):
        return run([sys.executable, "-I", SCRIPT, "spend", *args])

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

    def test_cost_that_is_not_a_number_fails_with_code_2(self):
        for name, text in (("null", '{"costUsd": null}'), ("nan", '{"costUsd": NaN}'), ("text", '{"costUsd": "1.5"}'),
                           ("minus", '{"costUsd": -1}'), ("turn", '{"total_cost_usd": null}')):
            with self.subTest(name):
                path = self.tmp / f"{name}.json"
                path.write_text(text, encoding="utf-8")
                self.assertResult(self.spend("--cap", "10", path), 2, "is not a number of 0 or more")

    def test_error_text_is_utf8_without_the_utf8_mode(self):
        path = self.tmp / "text.json"
        path.write_text('{"costUsd": "\u0436 \u4e2d"}', encoding="utf-8")
        result = run([sys.executable, "-I", "-X", "utf8=0", SCRIPT, "spend", "--cap", "10", path])
        self.assertResult(result, 2, "the cost '\u0436 \u4e2d' is not a number of 0 or more")

    def test_cap_and_rest_that_are_not_amounts_are_usage_errors(self):
        path = self.write_json("a/baseline.json", result_file(20.0, []))
        for args in (("--cap", "nan"), ("--cap", "10", "--rest", "nan"), ("--cap", "10", "--rest=-5"), ("--cap", "inf")):
            with self.subTest(args):
                self.assertResult(self.spend(*args, path), 2, "give a number of 0 or more")

    def test_sum_equal_to_the_cap_passes(self):
        path = self.write_json("a/baseline.json", result_file(8.0, []))
        self.assertIn("sum 10.00 USD, cap 10.00 USD", self.tool("spend", "--cap", "10", "--rest", "2", path))

    def test_file_that_is_not_json_fails_with_code_2(self):
        path = self.tmp / "cut.json"
        path.write_text('{"costUsd": 9.0, "cases": [', encoding="utf-8")
        self.assertResult(self.spend("--cap", "10", path), 2, "ERROR cannot read")

    def test_no_file_tests_the_rest_against_the_cap(self):
        self.assertIn("spent 0.00 USD, rest 4.00 USD", self.tool("spend", "--cap", "10", "--rest", "4"))
        self.tool("spend", "--cap", "3", "--rest", "4", code=3)

    def test_file_that_is_not_a_json_object_fails_with_code_2(self):
        path = self.tmp / "list.json"
        path.write_text("[1, 2]", encoding="utf-8")
        for command in (("spend", "--cap", "1"), ("runs",), ("kept",)):
            with self.subTest(command):
                self.assertResult(run([sys.executable, "-I", SCRIPT, *command, path]), 2, "is not a JSON object")


class KeptTests(EvalResultsCase):
    def test_each_kept_folder_once_in_order(self):
        path = self.write_json("b.json", result_file(1, [("with", 1, "B2", None), ("with", 1, "A1", None),
                                                         ("with", 1, "B2", None), ("with", 1, None, None)]))
        self.assertEqual(self.tool("kept", path), "- claude-eval-B2\n- claude-eval-A1\n")


class TraceTests(EvalResultsCase):
    def trace(self, *events, raw=b""):
        path = self.tmp / "trace.jsonl"
        path.write_bytes("".join(json.dumps(item) + "\n" for item in events).encode("utf-8") + raw)
        return path

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

    def test_output_is_utf8_without_the_utf8_mode(self):
        path = self.trace(event([{"type": "text", "text": "a \u2014 b \u4e2d"}]))
        result = run([sys.executable, "-I", "-X", "utf8=0", SCRIPT, "trace", path])
        self.assertResult(result, 0, "[assistant] TEXT a \u2014 b \u4e2d")

    def test_zero_max_lines_is_a_usage_error(self):
        self.assertResult(run([sys.executable, "-I", SCRIPT, "trace", TRACE, "--max-lines", "0"]), 2)

    def test_tool_result_and_text_content_print(self):
        path = self.trace(event("a plain text", role="user"),
                          event([{"type": "tool_result", "content": "r" * 30}], role="user", parentToolUseId="toolu_1"))
        out = self.tool("trace", path, "--limit", "20")
        self.assertEqual(out, "[user] a plain text\n[user sub] RESULT rrrrrrrrrr ... 20 more characters\n")

    def test_tool_result_of_the_fixture_prints(self):
        self.assertIn("[user sub] RESULT label not found\n", self.tool("trace", TRACE))

    def test_help_prints_the_exit_codes(self):
        self.assertResult(run([sys.executable, "-I", SCRIPT, "--help"]), 0, "Exit codes:", "over the cap")

    def test_line_of_another_shape_does_not_stop_the_trace(self):
        path = self.trace({"type": "x", "message": "plain"}, event({"type": "text"}), event(["plain"]),
                          event([{"type": "text", "text": "the last text"}]), raw=b'{"type": "assistant", "message": "\xff\n')
        out = self.tool("trace", path)
        self.assertIn("[assistant] TEXT the last text\n", out)
        self.assertIn("[line 5] NOT JSON, skipped", out)

    def test_text_with_a_line_break_stays_on_one_line(self):
        path = self.trace(event([{"type": "text", "text": "first\n[user] RESULT all tests passed"}]))
        self.assertEqual(self.tool("trace", path), '[assistant] TEXT "first\\n[user] RESULT all tests passed"\n')

    def test_default_output_of_long_tool_calls_is_below_the_limit_of_the_bash_tool(self):
        call = {"type": "tool_use", "name": "mcp__plugin_github_github__" + "x" * 37, "input": {"body": "y" * 20000}}
        path = self.trace(*[event([call], parent_tool_use_id="toolu_1") for _ in range(200)])
        out = self.tool("trace", path)
        self.assertLess(len(out), 30000)

    def test_default_output_is_below_the_limit_of_the_bash_tool(self):
        path = self.trace(*[event([{"type": "text", "text": "x" * 900}]) for _ in range(400)])
        out = self.tool("trace", path)
        self.assertLess(len(out), 30000)
        self.assertIn("more lines. Raise --max-lines to see them", out)


if __name__ == "__main__":
    unittest.main()
