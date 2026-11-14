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
| `review-loop` | `dev-essentials` | 5 | WSL |
| `subagent-orchestration` | `dev-essentials` | 4 | WSL |
| `process-pr-comments` | `dev-essentials` | 4 | WSL |
| `bug-hunt` | `dev-essentials` | 2 | WSL |
| `create-html-artifact` | `dev-essentials` | 2 | Windows, because it grants no shell tool |
| `feature-pipeline` | `dev-essentials` | 9 | WSL |
| `write-tests` | `dotnet-backend-dev` | 2 | WSL |
| `style-compare-openbsd` | `doc-styles` | 9 | Windows, because it grants no shell tool |
| `style-compare-se` | `doc-styles` | 9 | Windows, because it grants no shell tool |
| `style-compare-both` | `doc-styles` | 3 | Windows, because it grants no shell tool |

The count is the number of behavior cases. If a skill has trigger cases, the tag of its suite also selects them. So `--tag review-loop`, `--tag feature-pipeline`, and `--tag write-tests` also run the trigger cases in `evals/triggers/` of their plugin.

The `style-compare-*` suites compare the style of `doc-styles` with `simple-english`. The tag `style-compare` selects the cases of all `style-compare-*` suites. The suite `style-compare-openbsd` runs the skill on the documents in `evals/style-compare/openbsd/` of `doc-styles`. The suite `style-compare-se` runs the same prompts with `simple-english`, from `evals/style-compare/simple-english/`. The suite `style-compare-both` runs the documents in `evals/style-compare/coexist/` with both plugins loaded. The `simple-english` side loads the stand-in in `tests/evals/stubs/simple-english`, a byte copy of simple-english 2.1.1. If a newer simple-english is installed, a test fails, so that the copy does not fall behind in silence. The trigger cases of `doc-styles` in `evals/triggers/` carry the tag `openbsd-style-docs`, and its probes in `evals/probes/` carry the tag `probe`.

Run the suites through the compare script, because the cases of `dotnet-backend-dev` load `dev-essentials` from a `.deps` copy. A suite that grants `Bash` needs the sandbox of Claude Code, so run it in WSL2. Prepare WSL2 first:

1. Install `bubblewrap` and `socat`. The sandbox needs both.
2. For the `feature-pipeline` and `write-tests` suites, install the .NET SDK 10 outside your home folder. The sandbox cannot read your home folder, so an SDK in `~/.dotnet` does not work. On Ubuntu 26.04, the package `dotnet-sdk-10.0` works.
3. Set `TMPDIR` to a folder outside `/tmp`, `/var/tmp`, `/dev/shm`, and `/run/shm`, and make that folder. The sandbox of a run denies these four folders, and the run folder follows `TMPDIR`. If `TMPDIR` points to one of them, no Bash write works in the run. This is a bug of Claude Code ([anthropics/claude-code#104631](https://github.com/anthropics/claude-code/issues/104631)). The `run` and `baseline` commands stop with a message in this case.

This example runs the `review-loop` suite in WSL2. Pass `--scaffold`, because each case builds its repository with its `scaffold.sh`. Pass `--allow-tools`, because a run asks for no permission and grants no shell tool by default. If the shell does not find `claude`, pass its path with `--claude`.

```bash
export TMPDIR=$HOME/.cache/plugin-evals/tmp
mkdir -p "$TMPDIR"
python3 tests/evals/compare_versions.py baseline --plugin essentials/dev-essentials --commit <branch> --model <model id> --judge-model <model id> --scaffold --runs 3 --concurrency 3 --max-cost-usd <usd> --tag review-loop --out <folder> --allow-tools Bash Write Edit
```

A `scaffold.sh` script builds the repository of a case. It sources the functions in `evals/_lib/` of its plugin. The repository has a bare remote in `.remote/origin.git`, and each fixture commit has a subject that starts with `fixture:`. The cases with `mocks` answer the calls to the GitHub tools with mock files. They load the stand-in plugin in `tests/evals/stubs/github`, which declares the name of the server. The compare script copies the stand-in into `eval-stubs/` of the plugin copy. It is not in the plugin folder, because the claude.ai sync skips a plugin with a nested manifest. It is not in `evals/`, because `claude plugin eval` refuses a plugin that sits in the eval folder of the case. `claude plugin eval` also loads only plugins below the plugin under test.

The .NET cases need `-m:1`. The sandbox blocks the Unix sockets that the worker nodes of MSBuild need, so a plain `dotnet build` or `dotnet test` of a solution fails. With `-m:1`, MSBuild builds in one process, and the build works. So the prompt of each .NET case tells the agent to pass `-m:1`. The grader `route-plain-dotnet` counts the plain calls. A run has no network. The scaffold of a .NET case restores the packages into the shared folder `/tmp/plugin-evals/nuget`. Then it copies them into the home folder of the run, because the run cannot read `/tmp`.

The probes are cheap cases that test the run environment, not a skill. They are in `evals/probes/` of each plugin, and the tag is `probe`. Run them with the same command and `--tag probe` before the first paid suite run on a new machine.

Do not commit baseline files. A result file holds local temporary paths, so keep the baselines outside git.
