# Evals

An eval case is a prompt and its graders. A grader is a pass or fail check of a run. `claude plugin eval` runs the cases of a plugin and scores them. Each run calls a model on your account, so CI does not run the evals. The docs page [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) describes the case format.

The script `tests/evals/compare_versions.py` runs one suite on the plugin at a base commit and at a head commit. Then it compares the scores. Both sides run the cases of the head commit. This example runs the suite of `dev-essentials`:

```bash
python3 tests/evals/compare_versions.py run --plugin essentials/dev-essentials --base main --head HEAD --model <model id> --judge-model <model id> --out <folder>
```

Pass full model ids. The result files store them, because a comparison is valid only on the same models. The script writes `base.json`, `head.json`, and `report.md` into the `--out` folder. If the folder already holds a result file, the script stops. For a case that the report marks as unclear, the report prints the commands to run the case again and to compare all result files. To compare result files that you already have, use `compare --base <files> --head <files>`. For the rules of the verdict, run the script with `--help`.

A plugin with dependencies must run through this script. `claude plugin eval` loads only the plugin under test, so the plain command cannot load a dependency. The plugin then reports `dependency-unsatisfied` and does not load. The script copies each plugin that the manifest lists in `dependencies` from the marketplace at the same commit into `.deps/<name>` of the plugin copy. A case lists these copies in the `plugins` field of its `prompt.md`, for example `plugins: ["../../..", "../../../.deps/dev-essentials"]`. The trigger cases of `dotnet-backend-dev` do this, so they load only through the script.

To copy a plugin that the manifest does not list, pass `--extra-dep <name>` to `run` or `baseline` (repeat it for more plugins). The script copies it the same way, and a case lists it in `plugins`. The trigger cases of `doc-styles` use this for `dev-essentials`, because `doc-styles` must stay free of dependencies. The test `tests/test_eval_cases.py` accepts such a copy only for a plugin in `EVAL_ONLY_DEPS`. `baseline` also takes `--ablation none|with-without` (default `none`) and `--keep-temp`.

The script also copies each folder of `tests/evals/stubs/` into `eval-stubs/` of each plugin copy. A `run` uses the stand-ins of the head commit on both sides. A case entry points to `eval-stubs/<name>` of the plugin under test, for example `../../../eval-stubs/github`, so the case loads only through the script.

To record the result of one commit with no comparison, use `baseline`. It runs the suite at one commit with the same copy logic and writes `baseline.json` into the `--out` folder. If this file already exists, the script stops. This example records the trigger cases of `dotnet-backend-dev`:

```bash
python3 tests/evals/compare_versions.py baseline --plugin dotnet/dotnet-backend-dev --commit main --model <model id> --judge-model <model id> --tag triggers --out <folder>
```

Later, pass the file to `compare --base` or `compare --head`. `baseline` runs the cases of its own commit, but `run` runs the cases of the head on both sides. If two commits have different cases, do not compare their baseline files. If an eval fails or writes no case, `baseline` stops with exit code 2.

The trigger cases are in `evals/triggers/` of each plugin. In this file, a unit is a skill, an agent, or a command. Some units have the same trigger words in their descriptions. For each such pair, one case checks that the right unit starts. A near-miss case checks that the unit does not start for the words of the other unit. If another unit owns those words, the case also checks that this other unit starts. A grader with the name `<unit>-not-fired` checks that another unit did not start. The trigger cases use no shell tool, so they also run on native Windows. To run the trigger cases of a plugin without dependencies, run this command from the repository root:

```bash
claude plugin eval essentials/dev-essentials --ablation none --trust-plugin --no-publish --model <model id> --judge-model <model id> --tag triggers
```

To compare only the trigger cases at two commits, add `--tag triggers` to the command of the compare script. The run writes its results into `evals/results/` of the plugin. Git ignores this folder. A suite that grants `Bash` needs the sandbox of Claude Code, and native Windows has no sandbox. Run such a suite under WSL2.

## Behavior suites

A behavior suite is a set of eval cases that runs a workflow skill on a small planted repository. The graders check the result: the files, the commits, the pushes, and what the final message tells the user. Each suite is in `evals/` of its plugin, and the tag of its cases is the name of the suite.

| Suite | Plugin | Cases | Where it runs |
| --- | --- | ---: | --- |
| `review-loop` | `dev-essentials` | 6 | WSL |
| `subagent-orchestration` | `dev-essentials` | 4 | WSL |
| `process-pr-comments` | `dev-essentials` | 10 | WSL |
| `bug-hunt` | `dev-essentials` | 2 | WSL |
| `create-html-artifact` | `dev-essentials` | 2 | Windows, because it grants no shell tool |
| `feature-pipeline` | `dev-essentials` | 12 | WSL |
| `research-implement-review-report` | `dev-essentials` | 2 | WSL |
| `composers` | `dev-essentials` | 4 | WSL |
| `trim-artifacts` | `dev-essentials` | 1 | WSL |
| `audit-team` | `dev-essentials` | 1 | WSL |
| `optimize-skill` | `dev-essentials` | 1 | WSL |
| `merge-pr` | `dev-essentials` | 3 | WSL |
| `git-worktree-management` | `dev-essentials` | 1 | WSL |
| `write-tests` | `dotnet-backend-dev` | 2 | WSL |
| `style-compare-openbsd` | `doc-styles` | 9 | WSL2 or Linux, because its hook needs `python3` |
| `style-compare-se` | `doc-styles` | 9 | WSL2 or Linux, because its hooks need `python3` and `node` |
| `style-compare-both` | `doc-styles` | 3 | WSL2 or Linux, because its hooks need `python3` and `node` |

The count is the number of behavior cases. If a skill has trigger cases, the tag of its suite also selects them. So `--tag review-loop`, `--tag feature-pipeline`, `--tag merge-pr`, `--tag write-tests`, `--tag audit-team`, `--tag optimize-skill`, and `--tag git-worktree-management` also run the trigger cases in `evals/triggers/` of their plugin. The tag `composers` selects only the behavior cases. The trigger cases of its skills carry the tags `compose-pr`, `compose-task`, and `create-documentation`.

The sandbox of a run keeps `.git/worktrees` read-only ([#232](https://github.com/Vasar007/vasar-plugins-marketplace/issues/232)). So no eval case can make a git worktree. The case `gwm-create-blocked` tests the route and the report. Its run must call `worktree.py create`, and its final reply must say that the worktree was not made and why.

The case `os-review-fixes` gives one finding of the user in its prompt. So step 6 of `optimize-skill` always has an accepted finding to apply, on both sides of a comparison. The route grader `route-step6-reached` passes only for a run that made the second commit.

The `style-compare-*` suites compare the style of `doc-styles` with `simple-english`. The tag `style-compare` selects the cases of all `style-compare-*` suites. The suite `style-compare-openbsd` runs the skill on the documents in `evals/style-compare/openbsd/` of `doc-styles`. The suite `style-compare-se` runs the same prompts with `simple-english`, from `evals/style-compare/simple-english/`. The suite `style-compare-both` runs the documents in `evals/style-compare/coexist/` with both plugins loaded. The `simple-english` side loads the stand-in in `tests/evals/stubs/simple-english`, a byte copy of simple-english 2.1.1. If a newer simple-english is installed, a test fails, so that the copy does not fall behind in silence. The trigger cases of `doc-styles` in `evals/triggers/` carry the tag `openbsd-style-docs`, and its probes in `evals/probes/` carry the tag `probe`.

The hooks of these suites run as commands on the `PATH` of the run. The `PostToolUse` lint hook of `doc-styles` runs `python3`. The stand-in runs `node` in its `SessionStart` hook, and `python3` in its `PostToolUse` and `Stop` hooks. So run the `style-compare-*` suites and the probes of `doc-styles` in WSL2 or on Linux. There, install Python 3 as `python3` and Node.js 22 or later as `node`.

With Claude Code 2.1.325 in WSL2, `probe-obsd-lint-hook` and `probe-se-lint-hook` scored 1.00 with the plugin and 0.00 without it. On native Windows with the same version, both probes scored 0.00 with the plugin. There, the Python hooks gave no message in the eval run. Issue [#151](https://github.com/Vasar007/vasar-plugins-marketplace/issues/151) has the evidence. The cause is not proven.

Run the suites through the compare script, because the cases of `dotnet-backend-dev` load `dev-essentials` from a `.deps` copy. A suite that grants `Bash` needs the sandbox of Claude Code, so run it in WSL2. Prepare WSL2 first:

1. Install `bubblewrap` and `socat`. The sandbox needs both.
2. For the `feature-pipeline` and `write-tests` suites, install the .NET SDK 10 outside your home folder. The sandbox cannot read your home folder, so an SDK in `~/.dotnet` does not work. On Ubuntu 26.04, the package `dotnet-sdk-10.0` works. The scaffolds of these suites also need `flock` from util-linux. Ubuntu installs it by default.
3. Set `TMPDIR` to a folder outside `/tmp`, `/var/tmp`, `/dev/shm`, and `/run/shm`, and make that folder. The sandbox of a run denies these four folders, and the run folder follows `TMPDIR`. If `TMPDIR` points to one of them, no Bash write works in the run. This is a bug of Claude Code ([anthropics/claude-code#104631](https://github.com/anthropics/claude-code/issues/104631)). The `run` and `baseline` commands stop with a message in this case.
4. For the `style-compare-*` suites and the probes of `doc-styles`, install Node.js 22 or later in Linux. For example, unpack the tarball of nodejs.org into `~/.local/opt`. Then link the `bin/node` file of its top folder into `~/.local/bin`. Make sure that `node` and `python3` are on the `PATH` of Linux. A Windows install of Node.js does not help. The hook runs `node`, and WSL2 runs a Windows program only by its full name, `node.exe`.
5. Keep the clone for the eval runs in the Linux file system, for example in `~/src`. In WSL2, each file access on a Windows drive (a path below `/mnt/c`) is slow. The section [File storage and performance across file systems](https://learn.microsoft.com/en-us/windows/wsl/filesystems#file-storage-and-performance-across-file-systems) of the WSL docs recommends the Linux file system for Linux tools. If `git clone` or `cargo build` starts with a current folder on a Windows drive, WSL also shows a performance tip in Windows. WSL compares only the name of the program and its first argument. The source also lists `npm install`, but in a form that a normal `npm install` does not match. The target of the clone does not matter (file [`telemetry.cpp`](https://github.com/microsoft/WSL/blob/abce91d14bc6ed16943673ddf9984ae2f6e281af/src/linux/init/telemetry.cpp#L56-L58) of the WSL source). A `wsl.exe` command from Windows starts in the current Windows folder, which WSL2 sees as a path below `/mnt/c`. So start each such command in the Linux file system. In Git Bash or PowerShell, write `wsl.exe --cd '~' -e bash -lc '<command>'`. Keep the quotes around `~`, because Git Bash changes a bare `~` to the Windows home folder. In `cmd.exe`, write `wsl.exe --cd ~ -e bash -lc "<command>"`. To get a branch of a Windows clone, write a git bundle into the Linux file system. In Git Bash, in the Windows clone, run `git bundle create //wsl.localhost/<distribution>/home/<user>/work.bundle main <branch>`. Then fetch from that file in the Linux clone: `git fetch ~/work.bundle '+refs/heads/*:refs/remotes/win/*'`. The fetch puts the branch at `win/<branch>`, not at `<branch>`. So pass `win/<branch>` to the `--commit`, `--base`, or `--head` option of the compare script.

This example runs the `review-loop` suite in WSL2. Pass `--scaffold`, because each case builds its repository with its `scaffold.sh`. Pass `--allow-tools`, because a run asks for no permission and grants no shell tool by default. If the shell does not find `claude`, pass its path with `--claude`.

```bash
export TMPDIR=$HOME/.cache/plugin-evals/tmp
mkdir -p "$TMPDIR"
python3 tests/evals/compare_versions.py baseline --plugin essentials/dev-essentials --commit <branch> --model <model id> --judge-model <model id> --scaffold --runs 3 --concurrency 3 --max-cost-usd <usd> --tag review-loop --out <folder> --allow-tools Bash Write Edit
```

A `scaffold.sh` script builds the repository of a case. It sources the functions in `evals/_lib/` of its plugin. In `dotnet-backend-dev`, `git-fixture.sh` and `dotnet-fixture.sh` are git symlinks to the files of the same name in `essentials/dev-essentials/evals/_lib/`. Change only the files in `dev-essentials`. A checkout on Windows makes real links only with `core.symlinks=true` and either the Developer Mode of Windows or a shell with administrator rights. Without them, a test names the fix. The repository has a bare remote in `.remote/origin.git`, and each fixture commit has a subject that starts with `fixture:`. The cases with `mocks` answer the calls to the GitHub tools with mock files. They load the stand-in plugin in `tests/evals/stubs/github`, which declares the name of the server. The compare script copies the stand-in into `eval-stubs/` of the plugin copy. It is not in the plugin folder, because the claude.ai sync skips a plugin with a nested manifest. It is not in `evals/`, because `claude plugin eval` refuses a plugin that sits in the eval folder of the case. `claude plugin eval` also loads only plugins below the plugin under test.

A regex grader with the target `mock_calls` does not read the file `out/mock-calls.jsonl` of the run. Claude Code 2.1.325 builds the graded text from the tool calls of the trace. The text has one line for each mocked call, in the form `{"tool":"mcp__plugin_github_github__issue_write","input":...,"output":...,"verdict":"ok"}`. The `tool` field holds the full tool name, with the prefix of the server. The call file holds the short name, for example `issue_write`. The official docs do not say this.

So a pattern for a call names the `tool` field and accepts the prefix, for example `"tool":"(?:[\w-]*__)?issue_write"`. The simpler pattern `"tool":"\w*issue_write"` also matches the tool `sub_issue_write`. A bare tool name also matches the input or the output of another call. The graded text lacks the calls of a subagent of a subagent, because the trace does not hold them. The call file holds them. So a grader on `mock_calls` cannot see such a call.

Each pattern on `mock_calls` starts at the `tool` field of a call. A pattern that reads the input of the call reads only the line of that call. So it uses `[^\n]` and not `[\s\S]`, and each negated class such as `[^\]\n]` holds `\n`. Outside a negated class, it has no `\n`, `\s`, `\W`, or `\D`, because each of them also matches a line end. For example, it uses `[^\S\n]` in place of `\s`. An example is `"tool":"(?:[\w-]*__)?pull_request_review_write"[^\n]*?"method":"resolve_thread"`. A pattern for the order of two calls binds each call to a `tool` field, for example `"tool":"(?:[\w-]*__)?issue_write"[\s\S]*"tool":"(?:[\w-]*__)?issue_read"`. The field holds the prefix `(?:[\w-]*__)?` and one tool name or a group of names, such as `(?:issue_write|create_\w*)`. Between two fields, only `[\s\S]*` or `[\s\S]*?` can cross a line end. Outside a `tool` field, a pattern names no mocked tool. Each side of a `|` outside a group starts at a `tool` field. A grader on `mock_calls` has no flag `s`. The test `MockCallsGraderTests` in `tests/test_eval_cases.py` makes sure that each `mock_calls` grader of the repository has these forms. A `not_contains` grader can check the input of a call that the run must make, such as the create call of `cmp-issue-create`. That grader passes a run that makes no such call. So the case also needs a grader that fails a run with no call, for example `created`. A negative lookahead after the `tool` field is not a fix, because it passes a run in which only one of two calls is right.

To test a changed grader before a paid run, replay it on kept runs with `tests/evals/replay_graders.mjs`. A kept run is a run folder that `--keep-temp` keeps. The run folder of a stored result is its `tracePath` without `/out/trace.jsonl`. The tool needs Node.js 22 or later.

```bash
node tests/evals/replay_graders.mjs --case <case folder> <run folder>...
```

The tool builds the graded texts from `out/trace.jsonl` and `out/mocks/` of the run folder, by the rules of Claude Code 2.1.325. In the `mock_calls` text, a call with an error result has `"isError":true` before `verdict`. The verdict of a call is `ok`, `tool_error`, `no_result`, or `abort`.

The tool replays the regex graders on `last_message`, `mock_calls`, and `trace`, and the `tool_used` graders. It skips the `llm` and `baseline` graders, because they call a model. It skips the `file_exists` graders and the regex graders on `files` or on a file, because a kept run does not hold their text. It also skips a `tool_order` grader in the one-line form. A nested YAML block, for example `before:` of a `tool_order` grader on its own line, stops the tool with exit code 2. On 2026-11-16, it gave the stored verdict for all 1,913 replayed verdicts of 529 kept runs.

The tool prints one line for each grader of each run, with four fields that a tab separates: the run folder name, the grader name, `pass`, `fail`, or `skip`, and the reason. If a replayed grader fails, the exit code is 1. If an argument or an input file is wrong, it is 2.

The tool does not know the arm of a run, and it does not read the `arm` key of a grader. It replays each grader on each run that you give, and each failed grader gives exit code 1. The replay is not `claude plugin eval`, so a later Claude Code version can grade in another way. Like the graded text, the replay lacks the calls of a subagent of a subagent.

A mock of the type `agent` does not see a call that a fixed mock answered (Claude Code 2.1.325). In `cmp-issue-create`, a fixed mock answered the create call, and an agent mock answered the read-back call with another issue. So each run that read the issue back reported that the read-back did not match. A mock that reads back what an earlier call wrote gets a fixed fixture.

No mock can give the SHA of a commit that the run makes. The merge gate of `merge-pr` compares the head SHA of the pull request with the local branch. So two cases test the merge of `feature-pipeline` in the full mode. The case `fp-e2-merge` starts after Step 9, and its scaffold makes the head commit. Its run must merge. The case `fp-e2-merge-gate` is a full run. Its mock gives the last commit of the scaffold as the head, so the pull request lacks the commit of the run. Its run must read the gate and must not merge. `ScaffoldTests` in `tests/test_eval_scaffolds.py` makes sure that the head SHA in `fixtures/pull/get.json` of each case is the last commit of its scaffold.

A grader that must see no push is a `file_exists` grader with `exists: false` and the path `.remote/origin.git/logs/refs/heads/**`. Only `fp-e3-autonomous-main` reads `.remote/origin.git/logs/refs/heads/main`, because its run must push a work branch. The scaffold turns on the reflogs of the bare remote after its own push. So each later push of a branch writes a new file below that folder. In Claude Code 2.1.325, `**` also matches a branch name with a slash, such as `work/813`. A grader that must see no commit on a branch reads the reflog of that branch with `match: not_contains` and the pattern `\t(?!commit(?: \(initial\))?: fixture:|branch: Created from)`. Each reflog line that the fixture did not write fails it, except a `branch: Created from` line. Examples are a commit, an amend, a reset, a merge, a cherry-pick, a rebase, and a revert. `fp-e1-clean-change` also reads `.git/logs/HEAD`, so that a commit on a new branch fails too. `GraderBranchTests` and `CommitGraderTests` in `tests/test_eval_scaffolds.py` pin these forms. These seven forms still pass:

- A push of only a tag or of another ref outside `refs/heads`, such as `refs/pull/42/head`.
- A push that deletes a branch.
- A commit with a subject that starts with `fixture:`.
- A `git update-ref` with no message.
- A commit on a new branch in a linked worktree.
- A commit on a new branch in the main work tree, in each case other than `fp-e1-clean-change`.
- A branch that the run deletes and makes again at a new commit, in each case other than `fp-e1-clean-change`. If the commit is in a linked worktree, it passes in `fp-e1-clean-change` too.

A run sends one prompt, so a case cannot answer a question of the skill in a later turn. The session of a run also has no `SendMessage` tool (Claude Code 2.1.325). So the cases of this repository cannot test a resume of a subagent. A case gives the answers of the user in advance in its prompt instead, as `ppc-reshaped-fix` and `ppc-open-items-answered` do. Such a case tests what the skill does with an answer, but not that the skill stops and waits for it. The cases that end at a question, for example `ppc-gated-threads`, test the stop. The case format can also continue a recorded conversation with `context.history_file`, but no case of this repository uses it.

The .NET cases need `-m:1`. The sandbox blocks the Unix sockets that the worker nodes of MSBuild need, so a plain `dotnet build` or `dotnet test` of a solution fails. With `-m:1`, MSBuild builds in one process, and the build works. So the prompt of each .NET case tells the agent to pass `-m:1`. The grader `route-plain-dotnet` counts the plain calls. A run has no network. The scaffold of a .NET case restores the packages into the shared folder `/tmp/plugin-evals/nuget`. Then it copies them into the home folder of the run, because the run cannot read `/tmp`. A lock on `/tmp/plugin-evals/nuget.lock` lets only one scaffold at a time do the restore and the copy. So the scaffolds of parallel runs do not break each other.

The grader `route-plain-dotnet` of each .NET case reads the JSON text of the input of each Bash call. It counts a `dotnet build` or `dotnet test` command with no `-m:1`, `-m 1`, `-m=1`, or `-maxcpucount:1` after it. The command must be at the start of the input or of a line. It can also come after a `;`, `&`, `|`, `(`, or `{`. Some words can come before `dotnet`: `!`, `if`, `then`, `else`, `do`, `while`, `until`, `time`, and `env`. A `NAME=value` assignment can too, and so can `timeout` with its options and its time. The value of the assignment cannot have a space, a tab, a line break, a backslash, `;`, `&`, or `|`. So the grader does not count a sentence that names the command, for example in a heredoc or in the text of an `echo`. The grader does not read shell quotes or heredocs. So a run can get a wrong verdict in these forms:

- The grader misses a plain call after another word, such as `bash -c "dotnet build"`, `nice dotnet build`, or `timeout -k 5 300 dotnet build`. If a later command of the same Bash call has `-m:1`, the grader also misses the plain call before it. It also misses a plain call after an assignment with a space, `;`, `&`, or `|` in its value. Examples are `X="a b" dotnet build` and `F='A|B' dotnet test`. It also misses a path before `dotnet`, such as `$HOME/.dotnet/dotnet build`. It also misses a call that a backtick substitution wraps, such as `out=` followed by `dotnet test` in backticks.
- The grader counts a heredoc line that starts with `dotnet build` or `dotnet test`. It also counts the command after a `;`, `&`, `|`, `(`, or `{` in quoted text, such as `echo 'Build first; dotnet build is slow.'`.

This list is not complete. The class `RoutePlainDotnetGraderTests` in `tests/test_eval_cases.py` pins each of these forms.

The `tests-passed` graders of the .NET cases read the outcome of the last test run from the file `.test-runs/last.txt` of the workspace. The scaffold function `dotnet_write_run_marker` adds a test fixture that writes this file. At setup, the fixture makes the file `.test-runs/started-<ticks>` and writes `Started`. At teardown, it writes `Passed` or `Failed`. So a test run that stops before the teardown, for example on a crash or a timeout, leaves `Started`. The `tests-ran` graders look for a `started-` file.

The target `MarkTestOutcomeStale` in `Directory.Build.props` runs before a compile. It writes `Stale` to the file in two cases. In the first case, a source file, a project file, or a referenced assembly is newer than the compiled assembly. In the second case, the list of source files changed, for example by a deleted file. So a failed compile after a passing test run does not keep `Passed`. A build that compiles nothing keeps the outcome.

The marker has these limits:

- A rebuild, or a clean and a build, writes `Stale` with no change of the code.
- A new file time (`touch`, `git checkout`) also writes `Stale`.
- A first build of another configuration, for example `-c Release`, also writes `Stale`.
- An edit with no later build of its project keeps the outcome.
- A failed restore keeps the outcome.
- A change of only `.editorconfig` keeps the outcome, because that file is not an input of the target.
- `dotnet test --no-build` runs the last good binaries and writes their outcome.

The probes are cheap cases that test the run environment, not a skill. They are in `evals/probes/` of each plugin, and the tag is `probe`. Run them with the same command and `--tag probe` before the first paid suite run on a new machine.

The grader `untested-commit` of seven `dev-essentials` cases reads the trace. It fails a run that edits a `.py` file and then makes a `git commit` with no `unittest` run between them. An `Edit`, `Write`, or `MultiEdit` call on a `.py` file is an edit. A Bash command that writes a `.py` path with `>`, `>>`, or `tee` is an edit. A `sed -i` or `perl -pi` command with a `.py` path is an edit. The path must come before the next `;`, `&`, `|`, or line end. The grader does not read shell quotes. So a bad run can pass in these forms:

- The grader misses a `;`, `&`, or `|` inside a quoted script, such as `sed -i 's/a;b/c/' app/a.py` or `sed -i 's|a|b|' app/a.py`. It also misses `xargs sed -i`, `find -exec sed -i`, and the paths in a shell variable. It also misses `sed -Ei` and a script over more than one line. It also misses a `sed -i` at the start of the second line of a command. This list is not complete.

Four tries at a pattern that reads the script each brought a new wrong verdict, so the grader stays as it is (issue #162). The class `TestsBeforeCommitGraderTests` in `tests/test_eval_cases.py` pins each of these forms. It also makes sure that the grader needs less than 2 seconds for one command with 4000 `sed` edits or 4000 `-e` scripts.

Do not commit baseline files. A result file holds local temporary paths, so keep the baselines outside git.

## Clean the temp folder

The temp folder of your eval runs is the folder that `TMPDIR` names, for example `~/.cache/plugin-evals/tmp`. Nothing cleans this folder. `claude plugin eval` makes one `claude-eval-*` run folder in it for each run. At the end of the run, it deletes the run folder. With `--keep-temp`, it keeps the run folder and prints its path. A finished kept run folder holds the trace of the run in `out/trace.jsonl`. The kept folder is read-only, and its `sealed/` folder has no permissions, so a plain `rm -rf` cannot delete it.

The folder also collects leftovers. The run folders of stopped runs stay, and so do the `compare-versions-*` copies of the compare script. The .NET SDK, MSBuild, NuGet, and Python also leave temporary files there. After some weeks of runs, the folder can hold thousands of entries and several GB.

If one of your notes names an entry of the folder, the entry stays. If no eval run is active, each other entry can go. A note is a Markdown or text file in which you wrote the path of a run folder, for example to read its trace later. The result files and the logs of `claude plugin eval` name almost every run, so the commands below read only `.md` and `.txt` files. The commands do not read a note that is not UTF-8 text or whose name does not end in a lowercase `.md` or `.txt`. If a note is a link, the commands do not follow it. If a letter, digit, or `_` touches a name, the commands do not find it.

Do these steps in one shell of WSL2 or Linux:

1. Set the three folders. `EVAL_TMP` is the temp folder of your eval runs. `NOTES` is the folder of your notes. `LISTS` is a folder for the lists of the cleanup, outside `EVAL_TMP`.

   ```bash
   EVAL_TMP="$HOME/.cache/plugin-evals/tmp"
   NOTES="$HOME/eval-notes"
   LISTS="$HOME/.cache/plugin-evals/clean"
   ```

2. Make sure that no eval run is active. If the command prints a process, wait until that process ends.

   ```bash
   pgrep -af '[p]lugin eval|[c]ompare_versions\.py (run|baseline)' || echo "No eval run is active."
   ```

3. Make the lists. First the command deletes the lists of an earlier cleanup. `keep.txt` holds the entries that stay, and `delete.txt` holds the entries that go. If `EVAL_TMP` holds no `claude-eval-*` folder, the command stops. If `EVAL_TMP` is `/`, your home folder, or a system temp folder, the command also stops. The lists leave out a name with a line break. If the command prints the `Stop:` line, do not do steps 4 and 5.

   ```bash
   rm -f -- "${LISTS:?}/all.txt" "$LISTS/keep.txt" "$LISTS/delete.txt"
   if [ -n "$(find "${EVAL_TMP:?}" -maxdepth 1 -name 'claude-eval-*' -print -quit)" ] && [ -d "${NOTES:?}" ] \
     && ! printf '%s\n' / /tmp /var/tmp /dev/shm /run/shm "$(realpath -- "$HOME")" | grep -qxF -- "$(realpath -- "$EVAL_TMP")"; then
     mkdir -p "${LISTS:?}"
     find "$EVAL_TMP" -mindepth 1 -maxdepth 1 ! -name "$(printf '*\n*')" -printf '%f\n' | sort > "$LISTS/all.txt"
     grep -rhoFw -f "$LISTS/all.txt" --include='*.md' --include='*.txt' "$NOTES" | sort -u | comm -12 "$LISTS/all.txt" - > "$LISTS/keep.txt"
     comm -23 "$LISTS/all.txt" "$LISTS/keep.txt" > "$LISTS/delete.txt"
     wc -l "$LISTS/keep.txt" "$LISTS/delete.txt"
   else
     echo "Stop: EVAL_TMP is not the temp folder of your eval runs, or NOTES is not a folder."
   fi
   ```

4. Read `keep.txt` and `delete.txt`. This command prints the size of the entries in `delete.txt`. The command cannot read the `sealed/` folders, so the real size is larger.

   ```bash
   (cd -- "${EVAL_TMP:?}" && tr '\n' '\0' < "${LISTS:?}/delete.txt" | du -sch --files0-from=- 2>/dev/null | tail -n 1)
   ```

5. Delete the entries in `delete.txt`. The command works only in `EVAL_TMP`. If an eval run is active, the command stops. It gives each listed folder write permission, and then it deletes the folder. It does not follow a symbolic link out of `EVAL_TMP`.

   ```bash
   (
     cd -- "${EVAL_TMP:?}" || exit 1
     if pgrep -f '[p]lugin eval|[c]ompare_versions\.py (run|baseline)' > /dev/null; then echo "An eval run is active. Nothing is deleted."; exit 1; fi
     while IFS= read -r name; do
       if [ -d "$name" ] && [ ! -L "$name" ]; then chmod -R u+rwX -- "$name"; fi
       rm -rf -- "$name"
     done < "${LISTS:?}/delete.txt"
   )
   ```
