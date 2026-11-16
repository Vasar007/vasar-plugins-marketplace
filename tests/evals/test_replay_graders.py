"""Tests for tests/evals/replay_graders.mjs.

The tests replay graders on the hand-made run in fixtures/replay-run and call no model. They need Node.js.
"""
import json
import shutil
import unittest
from pathlib import Path

from support import tool_missing
from test_eval_cases import plugin_roots, split_frontmatter
from test_eval_front_matter import require_yaml, yaml, yaml_files
from testkit import ScratchCase, run

HERE = Path(__file__).resolve().parent
TOOL = HERE / "replay_graders.mjs"
RUN = HERE / "fixtures" / "replay-run"
NO_NODE = "node not found. Install Node.js 22 or later to test the replay tool."

# One grader for each form that the replay must read, and one for each grader kind that it skips.
GRADERS = {
    "agent-used": "# One Agent call.\ntype: tool_used\ntool: Agent\nmin: 1\nmax: 1\n",
    "create-error": "type: regex\ntarget: mock_calls\npattern: '\"isError\":true,\"verdict\":\"tool_error\"'\n",
    "issue-closed": "type: regex\ntarget: mock_calls\npattern: '\"state\":\"closed\"'\n",
    "issue-written-twice": ("type: regex\ntarget: mock_calls\npattern: '\"tool\":\"(?:\\w*__)?issue_write\"'\n"
                            "match: \"count:2\"\n"),
    "issue-read": "type: tool_used\ntool: mcp__plugin_github_github__issue_read\n",
    "judge": "type: llm\ncriteria: The reply names the issue.\n",
    "no-apology": "type: regex\npattern: 'can''t'\nmatch: not_contains\n",
    "no-push": "type: tool_used\ntool: Bash\ninput_match: 'git push'\nmin: 0\nmax: 0\n",
    "no-unmocked-call": ("type: regex\ntarget: mock_calls\npattern: 'plugin_other_other|\"tool\":\"Bash\"'\n"
                         "match: not_contains\n"),
    "pushed": "type: file_exists\npath: .remote/origin.git/logs/refs/heads/**\nexists: false\n",
    "readme-changed": "type: regex\ntarget: { source: file, path: README.md }\npattern: paging\n",
    "replied-last": "type: regex\npattern: '^replied on the pull request\\.$'\nflags: mi\n",
    "reply-no-result": ("type: regex\ntarget: mock_calls\npattern: "
                        "'add_reply_to_pull_request_comment\",\"input\":\\{[^}]*\\},\"verdict\":\"no_result\"'\n"),
    "review-aborted": "type: regex\ntarget: mock_calls\npattern: '\"verdict\":\"abort\"'\n",
    "subagent-lines": "type: regex\ntarget: trace\npattern: '\"parent_tool_use_id\":\"tu_2\"'\nmatch: \"count:5\"\n",
    "tab-in-reason": "type: regex\npattern: \"Created issue|\\t\"\n",
    "touched-files": "type: regex\ntarget: files\npattern: README\n",
    "trace-lines": "type: regex\ntarget: trace\npattern: '\\}\\n\\{'\nmatch: \"count:16\"\n",
}

EXPECTED = [
    "replay-run\tagent-used\tpass\tAgent called 1x (expected 1..1)",
    "replay-run\tcreate-error\tpass\tmatched \"isError\":true,\"verdict\":\"tool_error\"",
    "replay-run\tissue-closed\tfail\tpattern not found in mock_calls",
    "replay-run\tissue-read\tpass\tmcp__plugin_github_github__issue_read called 1x (expected 1..\u221e)",
    "replay-run\tissue-written-twice\tpass\tfound 2 matches (expected 2)",
    "replay-run\tjudge\tskip\tthe replay does not run llm graders",
    "replay-run\tno-apology\tpass\tpattern absent as expected",
    "replay-run\tno-push\tpass\tBash called 0x (expected 0..0)",
    "replay-run\tno-unmocked-call\tpass\tpattern absent as expected",
    "replay-run\tpushed\tskip\tthe replay does not run file_exists graders",
    "replay-run\treadme-changed\tskip\tthe kept run does not hold the target "
    "{\"source\":\"file\",\"path\":\"README.md\"}",
    "replay-run\treplied-last\tpass\tmatched ^replied on the pull request\\.$",
    "replay-run\treply-no-result\tpass\tmatched add_reply_to_pull_request_comment\",\"input\":\\{[^}]*\\},"
    "\"verdict\":\"no_result\"",
    "replay-run\treview-aborted\tpass\tmatched \"verdict\":\"abort\"",
    "replay-run\tsubagent-lines\tpass\tfound 5 matches (expected 5)",
    "replay-run\ttab-in-reason\tpass\tmatched Created issue| ",
    "replay-run\ttouched-files\tskip\tthe kept run does not hold the target \"files\"",
    "replay-run\ttrace-lines\tpass\tfound 16 matches (expected 16)",
]

# The mock_calls text of the fixture run, as Claude Code 2.1.325 builds it. Bash and the tool of the server
# "other", which no mock file names, are not in it.
MOCK_CALLS = [
    '{"tool":"mcp__plugin_github_github__issue_read","input":{"owner":"example-org","repo":"pager","issue_number":7},'
    '"output":"{\\"number\\":7,\\"title\\":\\"Add paging\\"}","verdict":"ok"}',
    '{"tool":"mcp__plugin_github_github__issue_write","input":{"method":"create","title":"Fix paging",'
    '"labels":["bug"]},"output":"label not found","isError":true,"verdict":"tool_error"}',
    '{"tool":"mcp__plugin_github_github__issue_write","input":{"method":"create","title":"Fix paging"},'
    '"output":"{\\"number\\":8}","verdict":"ok"}',
    '{"tool":"mcp__plugin_github_github__add_reply_to_pull_request_comment",'
    '"input":{"comment_id":9101,"body":"Fixed in #8."},"verdict":"no_result"}',
    '{"tool":"mcp__plugin_github_github__pull_request_review_write","input":{"method":"submit_pending",'
    '"event":"APPROVE"},"output":"eval aborted by mock 0123456789ab: the case does not allow a review",'
    '"isError":true,"verdict":"abort"}',
]


class ReplayCase(ScratchCase):
    def setUp(self):
        super().setUp()
        self.node = shutil.which("node")
        if self.node is None:
            tool_missing(self, NO_NODE)

    def write_case(self, graders):
        folder = self.tmp / "case" / "graders"
        folder.mkdir(parents=True)
        for name, front in graders.items():
            (folder / f"{name}.md").write_text(f"---\n{front}---\nThe grader of the test.\n", encoding="utf-8")
        return folder.parent

    def replay(self, *args):
        return run([self.node, TOOL, *args])

    def module_call(self, expression):
        """Import the tool as a module, print the JSON of expression, and return the parsed value."""
        script = f"import * as t from {json.dumps(TOOL.as_uri())};\nconsole.log(JSON.stringify({expression}));"
        result = run([self.node, "--input-type=module", "-e", script])
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)


class ReplayTests(ReplayCase):
    def test_the_fixture_run_gives_the_pinned_verdicts(self):
        result = self.replay("--case", self.write_case(GRADERS), RUN)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), EXPECTED)

    def test_the_mock_calls_text_is_pinned(self):
        text = self.module_call(f"t.mockCallsText(t.readRun({json.dumps(str(RUN))}))")
        self.assertEqual(text.split("\n"), MOCK_CALLS)

    def test_the_last_message_is_the_text_of_the_last_assistant_message(self):
        last = self.module_call(f"t.readRun({json.dumps(str(RUN))}).lastMessage")
        self.assertEqual(last, "Created issue 8.\nReplied on the pull request.")

    def test_no_failed_grader_gives_exit_0(self):
        result = self.replay("--case", self.write_case({"agent-used": GRADERS["agent-used"]}), RUN)
        self.assertResult(result, 0, "replay-run\tagent-used\tpass\t")

    def test_a_run_without_mock_files_fails_a_mock_calls_grader(self):
        bare = self.tmp / "bare-run"
        (bare / "out").mkdir(parents=True)
        shutil.copy(RUN / "out" / "trace.jsonl", bare / "out" / "trace.jsonl")
        result = self.replay("--case", self.write_case({"review-aborted": GRADERS["review-aborted"]}), bare)
        self.assertResult(result, 1, "bare-run\treview-aborted\tfail\tno mock stand-ins were active in this run "
                          "(--mocks off, or no mocks/ directory applies to this case) \u2014 a mock_calls grader "
                          "has nothing to check")

    def test_a_skipped_grader_does_not_change_the_exit_code(self):
        graders = {"agent-used": GRADERS["agent-used"], "judge": GRADERS["judge"]}
        result = self.replay("--case", self.write_case(graders), RUN)
        self.assertResult(result, 0, "replay-run\tjudge\tskip\t")

    def test_an_abort_text_with_another_nonce_is_a_tool_error(self):
        run = ("{toolCalls: [{name: 'x', input: {}, output: 'eval aborted by mock ffffffffffff: stop', isError: true}], "
               "mocked: new Set(['x']), nonce: '0123456789ab'}")
        text = self.module_call(f"t.mockCallsText({run})")
        self.assertIn('"verdict":"tool_error"', text)

    def test_a_regex_grader_takes_its_pattern_from_the_body(self):
        folder = self.tmp / "case" / "graders"
        folder.mkdir(parents=True)
        (folder / "issue-closed.md").write_text("---\ntype: regex\ntarget: mock_calls\n---\n\"state\":\"closed\"\n",
                                                encoding="utf-8")
        (folder / "one-reply.md").write_text("---\ntype: regex\nmatch: count:1\n---\n\nReplied\n", encoding="utf-8")
        result = self.replay("--case", folder.parent, RUN)
        self.assertResult(result, 1, "replay-run\tissue-closed\tfail\tpattern not found in mock_calls",
                          "replay-run\tone-reply\tpass\tfound 1 matches (expected 1)")

    def test_the_front_matter_is_split_as_claude_code_splits_it(self):
        folder = self.tmp / "case" / "graders"
        folder.mkdir(parents=True)
        (folder / "README.md").write_text("Notes about the graders.\n", encoding="utf-8")
        (folder / "bom.md").write_text("\ufeff---\ntype: regex\npattern: Replied\n---\n", encoding="utf-8")
        (folder / "dash.md").write_text("---\ntype: regex\npattern: Replied---x\n---\n", encoding="utf-8")
        result = self.replay("--case", folder.parent, RUN)
        self.assertResult(result, 0, "replay-run\tbom\tpass\tmatched Replied", "replay-run\tdash\tpass\tmatched Replied")
        self.assertNotIn("README", result.stdout)

    def test_a_bad_pattern_fails_its_grader_only(self):
        graders = {"bad": "type: regex\npattern: '[unclosed'\n", "agent-used": GRADERS["agent-used"]}
        result = self.replay("--case", self.write_case(graders), RUN)
        self.assertResult(result, 1, "replay-run\tagent-used\tpass\t", "replay-run\tbad\tfail\tgrader threw: ")


class InputErrorTests(ReplayCase):
    def test_no_case_gives_exit_2(self):
        self.assertResult(self.replay(RUN), 2, "give --case and at least one run folder", "Usage:")

    def test_no_run_folder_gives_exit_2(self):
        self.assertResult(self.replay("--case", self.write_case(GRADERS)), 2, "give --case")

    def test_an_unknown_option_gives_exit_2(self):
        self.assertResult(self.replay("--case", self.write_case(GRADERS), "--json", RUN), 2, "Usage:")

    def test_a_run_folder_without_a_trace_gives_exit_2(self):
        result = self.replay("--case", self.write_case(GRADERS), self.tmp)
        self.assertResult(result, 2, "no trace: ")
        self.assertEqual(result.stdout, "")

    def test_a_nested_front_matter_block_gives_exit_2(self):
        graders = {"order": "type: tool_order\nbefore:\n  tool: Bash\nafter:\n  tool: Agent\n"}
        self.assertResult(self.replay("--case", self.write_case(graders), RUN), 2,
                          "front matter line that the replay cannot read:   tool: Bash")

    def test_a_comment_after_a_plain_value_gives_exit_2(self):
        graders = {"agent-used": "type: tool_used\ntool: Agent\nmin: 1 # at least one\n"}
        self.assertResult(self.replay("--case", self.write_case(graders), RUN), 2,
                          "plain value that the replay cannot read: 1 # at least one")

    def test_a_plain_value_that_yaml_does_not_read_as_text_gives_exit_2(self):
        for value in ("#8", "Error:", "- x", "a: b", "@x"):
            with self.subTest(value=value):
                shutil.rmtree(self.tmp / "case", ignore_errors=True)
                case = self.write_case({"named": f"type: regex\npattern: {value}\n"})
                self.assertResult(self.replay("--case", case, RUN), 2, f"plain value that the replay cannot read: {value}")

    def test_a_front_matter_without_a_closing_line_gives_exit_2(self):
        folder = self.tmp / "case" / "graders"
        folder.mkdir(parents=True)
        (folder / "open.md").write_text("---\ntype: regex\npattern: Replied\n", encoding="utf-8")
        self.assertResult(self.replay("--case", folder.parent, RUN), 2, "the front matter has no closing --- line")

    def test_graders_in_case_yaml_give_exit_2(self):
        case = self.write_case({"agent-used": GRADERS["agent-used"]})
        (case / "case.yaml").write_text('schema_version: "1.1"\nname: c\ngraders:\n  - name: x\n    type: llm\n'
                                        '    criteria: x\n', encoding="utf-8")
        self.assertResult(self.replay("--case", case, RUN), 2, "lists graders")

    def test_a_grader_without_a_type_gives_exit_2(self):
        graders = {"typo": "typ: regex\npattern: Replied\n"}
        self.assertResult(self.replay("--case", self.write_case(graders), RUN), 2, "the front matter has no type key")

    def test_a_graders_folder_without_a_grader_gives_exit_2(self):
        self.assertResult(self.replay("--case", self.write_case({}), RUN), 2, "no grader file with front matter")


class FrontMatterTest(ReplayCase):
    def test_the_reader_agrees_with_pyyaml_on_every_grader_file(self):
        require_yaml(self)
        files = [path for root in plugin_roots() for path in yaml_files(root) if path.parent.name == "graders"]
        self.assertTrue(files, "No grader file found.")
        script = (f"import fs from 'node:fs';\nimport * as t from {json.dumps(TOOL.as_uri())};\n"
                  "const paths = JSON.parse(fs.readFileSync(0, 'utf8'));\n"
                  "console.log(JSON.stringify(paths.map((p) => t.readFrontMatter(fs.readFileSync(p, 'utf8')))));")
        result = run([self.node, "--input-type=module", "-e", script], stdin=json.dumps([str(path) for path in files]))
        self.assertEqual(result.returncode, 0, result.stderr)
        mismatches = []
        for path, fields in zip(files, json.loads(result.stdout)):
            lines, _body = split_frontmatter(path.read_text(encoding="utf-8"))
            if fields != yaml.safe_load("\n".join(lines)):
                mismatches.append(path.as_posix())
        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()
