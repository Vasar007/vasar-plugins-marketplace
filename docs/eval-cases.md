# Eval cases and graders

This page is for a contributor who adds or changes an eval case or a grader. It gives the rules of this repository and the known limits of its graders. To run the cases, read [Evals](evals.md). The docs page [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) describes the case format.

The section "New and imported units" of [`CLAUDE.md`](../CLAUDE.md) says which cases a new unit needs. Each case must be able to fail for a real defect of its unit.

## Where the cases are

| Folder | What it holds |
| --- | --- |
| `evals/triggers/` of a plugin | The trigger cases and the near-miss cases. Their tags are `triggers` and the name of the unit |
| `evals/<suite>/<case>/` of a plugin | The behavior cases of a suite. The tag is the name of the suite |
| `evals/probes/` of a plugin | The probes of the run environment, with the tag `probe` |
| `evals/_lib/` of a plugin | The shell functions that the scaffolds source |
| `tests/evals/stubs/` | The stand-in plugins: `github` for the mocks of the GitHub tools, and `simple-english` |

A unit is a skill, an agent, or a command. Some units have the same trigger words in their descriptions. For each such pair, a trigger case tests that the right unit starts. A near-miss case tests that the unit does not start for the words of the other unit. A grader with the name `<unit>-not-fired` tests that another unit did not start.

In `dotnet-backend-dev`, `evals/_lib/git-fixture.sh` and `evals/_lib/dotnet-fixture.sh` are git symlinks to the files of `essentials/dev-essentials/evals/_lib/`. Change only the files in `dev-essentials`. On Windows, a clone makes real links only with `core.symlinks=true`, and with the Developer Mode of Windows or a shell with administrator rights. Without them, a test names the fix.

The stand-ins are outside the plugin folders, because the claude.ai sync skips a plugin with a second manifest. They are not in `evals/`, because `claude plugin eval` refuses a plugin in the eval folder of the case. The stand-in `simple-english` is a byte copy of simple-english 2.1.1. If a newer simple-english is installed, a test fails, so that the copy does not fall behind in silence.

## The tests of the cases

These tests read the cases and call no model:

- `tests/test_eval_cases.py` reads each case and each grader. It also tests the patterns of many graders on built traces.
- `tests/test_eval_front_matter.py` parses the YAML of each `prompt.md`, `case.yaml`, and grader file with PyYAML. `claude plugin eval` does not load a case whose YAML does not parse.
- `tests/test_eval_scaffolds.py` runs each `scaffold.sh` in a temporary folder. It also tests some graders on real git states.

A case that lists a copy in `.deps/` must name a dependency of its plugin. For a copy of `--extra-dep`, add the plugin to `EVAL_ONLY_DEPS` in `tests/test_eval_cases.py`.

## Scaffolds

A `scaffold.sh` script builds the repository of a case. It sources the functions in `evals/_lib/` of its plugin. The repository has a bare remote in `.remote/origin.git`. Each fixture commit has a subject that starts with `fixture:`.

The sandbox of a run keeps `.git/worktrees` read-only ([#232](https://github.com/Vasar007/vasar-plugins-marketplace/issues/232)). So no case can make a git worktree. The case `gwm-create-blocked` tests the route and the report instead.

### The .NET cases

A plain `dotnet build` or `dotnet test` of a solution fails in the sandbox. The sandbox blocks the Unix sockets that the worker nodes of MSBuild need. With `-m:1`, MSBuild builds in one process, and the build works. So the prompt of each .NET case tells the agent to pass `-m:1`. The grader `route-plain-dotnet` counts the plain calls.

A run has no network. The scaffold of a .NET case restores the packages into the shared folder `/tmp/plugin-evals/nuget`. Then it copies them into the home folder of the run, because the run cannot read `/tmp`. A lock on `/tmp/plugin-evals/nuget.lock` lets only one scaffold at a time do the restore and the copy.

### The test marker of the .NET cases

The `tests-passed` graders of the .NET cases read the outcome of the last test run from `.test-runs/last.txt` of the workspace. The scaffold function `dotnet_write_run_marker` adds a test fixture that writes this file. At setup, the fixture makes the file `.test-runs/started-<ticks>` and writes `Started`. At teardown, it writes `Passed` or `Failed`. So a test run that stops before the teardown leaves `Started`. The `tests-ran` graders look for a `started-` file.

The target `MarkTestOutcomeStale` in `Directory.Build.props` runs before a compile. It writes `Stale` to the file in two cases. In the first case, a source file, a project file, or a referenced assembly is newer than the compiled assembly. In the second case, the list of source files changed, for example by a deleted file. So a failed compile after a passing test run does not keep `Passed`. A build that compiles nothing keeps the outcome.

The marker has these limits:

- A rebuild, or a clean and a build, writes `Stale` with no change of the code.
- A new file time (`touch`, `git checkout`) also writes `Stale`.
- A first build of another configuration, for example `-c Release`, also writes `Stale`.
- An edit with no later build of its project keeps the outcome.
- A failed restore keeps the outcome.
- A change of only `.editorconfig` keeps the outcome, because that file is not an input of the target.
- `dotnet test --no-build` runs the last good binaries and writes their outcome.

## Mocks and prompts

A case with `mocks` answers the calls to the GitHub tools with mock files. It loads the stand-in plugin `github`, which declares the name of the server. These facts come from Claude Code 2.1.325:

- A mock of the type `agent` does not see a call that a fixed mock answered. So a mock that reads back what an earlier call wrote gets a fixed fixture.
- No mock can give the SHA of a commit that the run makes. The merge gate of `merge-pr` compares the head SHA of the pull request with the local branch. So a merge case starts after the commit, and its scaffold makes the head commit. Examples are `fp-e2-merge` and `rirr-merge`. A gate case gives an older head, so its run must not merge, as in `fp-e2-merge-gate`. `ScaffoldTests` makes sure that the head SHA in `fixtures/pull/get.json` of each case is the last commit of its scaffold.
- A run sends one prompt, and its session has no `SendMessage` tool. So a case cannot answer a question of the skill, and it cannot test a resume of a subagent. A case gives the answers of the user in advance in its prompt, as `ppc-reshaped-fix` does. A case that ends at a question, such as `ppc-gated-threads`, tests the stop.

The case format can also continue a recorded conversation with `context.history_file`. No case of this repository uses it.

## Write a grader

### Patterns on mock_calls

A regex grader with the target `mock_calls` does not read the file `out/mock-calls.jsonl`. Claude Code builds the graded text from the tool calls of the trace. The text has one line for each mocked call:

```text
{"tool":"mcp__plugin_github_github__issue_write","input":...,"output":...,"verdict":"ok"}
```

The `tool` field holds the full tool name, with the prefix of the server. The call file holds the short name. The official docs do not say this. The text lacks the calls of a subagent of a subagent, so no grader on `mock_calls` can see them.

A pattern on `mock_calls` follows these rules. `MockCallsGraderTests` makes sure that each such grader of the repository has these forms:

- It starts at the `tool` field and accepts the prefix, for example `"tool":"(?:[\w-]*__)?issue_write"`. The shorter `"tool":"\w*issue_write"` also matches `sub_issue_write`.
- It reads the input of a call only on the line of that call. So it uses `[^\n]` and not `[\s\S]`, and each negated class holds `\n`. Outside a negated class, it has no `\n`, `\s`, `\W`, or `\D`. For example, it uses `[^\S\n]` in place of `\s`.
- A pattern for the order of two calls binds each call to a `tool` field. Only `[\s\S]*` or `[\s\S]*?` crosses a line end between two fields.
- It names no mocked tool outside a `tool` field. Each side of a `|` outside a group starts at a `tool` field. It has no flag `s`.

An example is `"tool":"(?:[\w-]*__)?pull_request_review_write"[^\n]*?"method":"resolve_thread"`.

A `not_contains` grader on the input of a call passes a run that makes no such call. So the case also needs a grader that fails a run with no call, as `created` of `cmp-issue-create` does. A negative lookahead is no fix, because it passes a run in which only one of two calls is right.

### No push and no commit

A grader that must see no push is a `file_exists` grader with `exists: false` and the path `.remote/origin.git/logs/refs/heads/**`. The scaffold turns on the reflogs of the bare remote after its own push. So each later push of a branch writes a new file below that folder. `**` also matches a branch name with a slash, such as `work/813`. Only `fp-e3-autonomous-main` reads `.remote/origin.git/logs/refs/heads/main`, because its run must push a work branch.

A grader that must see no commit on a branch reads the reflog of that branch with `match: not_contains` and this pattern:

```text
\t(?!commit(?: \(initial\))?: fixture:|branch: Created from)
```

Each reflog line that the fixture did not write fails it, except a `branch: Created from` line. `fp-e1-clean-change` also reads `.git/logs/HEAD`, so that a commit on a new branch fails too. Some forms still pass, for example a push of only a tag, a push that deletes a branch, and a commit on a new branch. `GraderBranchTests` and `CommitGraderTests` in `tests/test_eval_scaffolds.py` pin each such form.

### Files of the project

A `file_exists` grader sees only the files that the run created. It does not see an edit or a delete of a file that the scaffold made. So a grader that must catch an edit compares the whole file with the file of the scaffold. `bh-planted-bugs` and `bh-flow` do this for the files with a planted bug. No grader reads the other files of their projects, so an edit of such a file passes.

### Long traces

The `claude` binary runs the regex graders in Bun 1.4.4, which uses the JavaScriptCore engine. In Bun, a long search can end with no match and no error. Then a grader fails a right run, and a `not_contains` grader passes a wrong run. No result shows it ([#319](https://github.com/Vasar007/vasar-plugins-marketplace/issues/319)).

So a trace grader that spans a large text uses few steps for each character. A plain `[\s\S]*` costs the least. In `tests-before-commit` and `untested-commit`, the token runs its lookahead only at a quote, and a run of other characters is one class term.

### Replay graders on kept runs

To test a changed grader before a paid run, replay it on kept runs. A kept run is a run folder that `--keep-temp` keeps. The run folder of a stored result is its `tracePath` without `/out/trace.jsonl`. The tool needs Node.js 22 or later.

```bash
node tests/evals/replay_graders.mjs --case <case folder> <run folder>...
```

- The tool builds the graded texts from `out/trace.jsonl` and `out/mocks/` of the run folder. In the `mock_calls` text, a call with an error result has `"isError":true` before `verdict`. The verdict of a call is `ok`, `tool_error`, `no_result`, or `abort`.
- It replays the regex graders on `last_message`, `mock_calls`, and `trace`, and the `tool_used` graders. It skips the `llm`, `baseline`, and `file_exists` graders, and the regex graders on `files` or on a file. It also skips a `tool_order` grader in the one-line form.
- It prints one line for each grader of each run, with four fields that a tab separates: the run folder, the grader, `pass`, `fail`, or `skip`, and the reason.
- If a replayed grader fails, the exit code is 1. If an argument or an input file is wrong, it is 2. A nested YAML block, such as `before:` of a `tool_order` grader on its own line, also gives exit code 2.
- It does not know the arm of a run, and it does not read the `arm` key of a grader.

The replay runs in Node.js, which uses the V8 engine. So a replay is no full proof for a grader that spans a large text. To find the verdict of the eval tool, run the pattern in Bun 1.4.4 on the trace. A later Claude Code version can also grade in another way.

## Known limits of the graders

Some graders read shell commands with a regex, so a rare command form gets a wrong verdict. The test class of each grader lists its known wrong verdicts. If a pattern change fixes one, change that list too. The classes are in `tests/test_eval_cases.py`, unless a line names another file.

These graders do not read shell quotes or heredocs. So a quoted text can count as a command, and a wrapped command can stay hidden:

- `route-no-branch` of `it-no-worktree-dirty` (`NoWorktreeDirtyRouteGraderTests`).
- `route-snapshot-script` and `route-delete-temp` of `bh-flow` (`BugHuntFlowGraderTests`).
- `route-probe-made` of `wm-scratch-probe` (`ScratchProbeGraderTests`).
- `route-plain-dotnet` of each .NET case (`RoutePlainDotnetGraderTests`).
- `integration-after-edit` of `so-integration-proof` (`IntegrationProofGraderTests`). The words of a test run in a commit message count as a run, and a `sed -i` edit after the run stays hidden.
- `route-smoke-run` of `so-no-integration-proof` (`NoIntegrationProofGraderTests`).
- `untested-commit` of the `dev-essentials` cases that edit Python files (`TestsBeforeCommitGraderTests`). Four tries at a better pattern each failed, so it stays ([#162](https://github.com/Vasar007/vasar-plugins-marketplace/issues/162)).

These graders have other known limits:

- `route-no-worktree-read` (`NoWorktreeReadGraderTests`): a harmless `branch` word before the read fails a right run. In Bun 1.4.4, a read after about 300,000 characters gives no match.
- `one-commit` and `one-commit-per-task` (`NoWorktreeBranchGraderTests` in `tests/test_eval_scaffolds.py`): an amend, a merge, a cherry-pick, or a rebase fails the run. `one-commit-per-task` cannot tell a task with two commits from a final review commit.
- `test-unchanged` of `fp-e5-breaking-change` (`BreakingChangeTestGraderTests`): it does not see `Assert.Ignore` in a `[SetUp]` method, a filter in the test command, or a moved test.
- `no-code-edit` of `hrp-post-one` (`HelpReviewPrPostGraderTests`): it does not see a change through Bash.
- `no-proof-named` of `so-no-integration-proof` (`NoIntegrationProofGraderTests`): a reply that says that the change needs no integration test passes it. So does a reply that says that no test failed in the receipt code.
- `route-gap-named` of `so-no-integration-proof` (`NoIntegrationProofGraderTests`): a reply that says that the run did not yet add such a test passes it. So does a reply that chose not to add such a test, or that says that there is no need to add one. A reply that names the test only as "one" fails it, for example "Consider adding one". So does a reply with no verb of adding, for example "Consider an integration test".
