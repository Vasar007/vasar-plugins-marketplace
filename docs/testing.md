# Testing

This page is for a contributor who changes this marketplace. It tells you how to run the tests, what they cover, and what CI runs. The tests are in `tests/`, outside every plugin folder, so no plugin cache gets them.

## Run the tests

Run all tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

To run one test module, run it from the folder `tests`:

```bash
cd tests
python3 -m unittest -v test_worktree
```

The whole suite passes only on Linux. On Windows, run it in WSL2 with `tools/wsl/unit-tests.sh`. See [Maintainer tools](tools.md#run-the-unit-suite-and-eval-runs-in-wsl2).

The two linters read only the files that git tracks. If you add a new `.md` file, run `git add` on it before you run the tests.

## Requirements

All tests need Python 3, Git, and Claude Code (the `claude` command). Some tests need more tools. If such a tool is missing, the test skips on your machine and fails in CI.

| Tool | Tests that need it |
| --- | --- |
| Node.js 22 or later | markdownlint, which runs `markdownlint-cli` through `npx`, and the tests of `tests/evals/replay_graders.mjs` |
| Bash | The tests of the `kb` scripts and the scaffold tests of the eval cases |
| .NET SDK 10 or newer, with the .NET 10 runtime | One scaffold test that builds a .NET solution |
| The simple-english linter | The prose lint of each `.md` file |
| PyYAML | The YAML test of the eval cases. It fails, and does not skip, with no PyYAML. The step `Install PyYAML` of `.github/workflows/tests.yml` names the version |

Under WSL2, install Node.js in Linux. The `npx` of a Windows install cannot run in a folder of the Linux file system, so the markdownlint test skips.

## What the suite covers

| Group | Test modules | A test fails for |
| --- | --- | --- |
| Plugin scripts | `test_<script>.py` for each script of a plugin, and `test_kb_plugin.py` | A wrong result of a script that a skill, a command, or a hook runs |
| Maintainer tools | `test_changelog_merge.py`, `test_eval_results.py`, `test_release.py`, and `test_tools_wsl.py` | A wrong result of a script in `tools/` |
| Lint of the text | `test_simple_english.py`, `test_markdownlint.py`, `test_readme_counts.py`, `test_prompt_phrases.py` | A lint hit, a count of units in the docs, or a request to show the reasoning |
| Rules in the units | `test_work_modes_*.py`, `test_review_loop_text.py`, `test_model_ladder_text.py`, and `test_rule_references.py` | A rule that leaves a unit, or a reference to a rule that does not exist |
| Manifests and versions | `test_plugin_cli.py`, `test_claude_ai_sync.py`, `test_version_bump.py` | A failed `claude plugin validate --strict`, a cost over budget, a key that the sync drops, or no new version |
| Eval cases | `test_eval_*.py` and the tests in `tests/evals/` | A case that does not load, a scaffold that fails, or a grader with a wrong verdict on a known run |
| Test helpers | `test_testkit.py` and `test_support.py` | A wrong result of a helper of the tests |

No eval test calls a model. [Eval cases and graders](eval-cases.md) says more about the eval tests.

## The linters

The simple-english test first looks for the linter in the folder that the variable `SIMPLE_ENGLISH_DIR` names. This folder is the root of a clone of SimpleEnglish. Then the test looks in the plugin cache. If it finds no linter, it skips.

A lint hit fails the test, unless `tests/simple-english-baseline.json` lists it with a reason. The `excluded` key of that file lists the folders that the test skips, each with a reason. A baseline entry with no hit fails the test, and so does an `excluded` folder with no tracked `.md` file. The baseline is for simple-english 2.1.1, so another linter version can report other hits.

The markdownlint rules are in `.markdownlint.jsonc`. Each rule that the file turns off has a comment with the reason.

## The tests of the plugin commands

The tests of `claude plugin validate` and `claude plugin details` give each call an empty, temporary configuration folder. They also remove the environment variables that sign Claude Code in, for example `CLAUDE_CODE_OAUTH_TOKEN`. So they need no sign-in, and they do not load your installed plugins.

The budget test keeps the always-on cost of each plugin below its budget in `tests/test_plugin_cli.py`. The always-on cost is the tokens that the names and the descriptions of the skills, agents, and commands add to every session. With no sign-in, `claude plugin details` shows an estimate: the characters divided by 4. A signed-in session shows a higher count from the API. So the test multiplies the estimate by `SIGNED_IN_RATIO` (1.5, measured on the present budgets).

A new default model or a much smaller budget can need a new ratio. Then compare the output of `claude plugin details <plugin>` in a signed-in session with the estimate of the test, and raise `SIGNED_IN_RATIO`.

## The version bump test

Each plugin with a changed file must have a higher `version` in its `plugin.json` than on the base branch. The test compares the work tree with the merge base of `HEAD` and the base branch. In CI for a pull request, the base branch is the target branch. On your machine, it is `origin/main`, or the branch that the variable `VERSION_BUMP_BASE` names. CI skips the test for a push to `main`, because the pull request ran it.

## CI

The workflow `.github/workflows/tests.yml` runs on each pull request and on each push to `main`. A new push to a pull request cancels the earlier run of that pull request. A run for a push to `main` is never cancelled while it runs.

The job `test` runs the whole suite on Linux. It installs the latest Claude Code, the .NET SDK 10, PyYAML, and the latest release of SimpleEnglish. It also fetches the full history, so that the version bump test finds the merge base. A new linter release can make the lint test fail. Treat that as a blocker: open an issue and fix it at once in its own pull request.

The job `test-windows` runs the tests of the plugin scripts, the maintainer tools, and the test helpers in Git Bash on Windows. These scripts have Windows paths: Git Bash, PowerShell, junctions, CRLF line ends, read-only files, and the stop of a process with `taskkill`. The job needs no linter, no Claude Code, no .NET, and no Node.js. The step "Run the tests of the plugin scripts and the maintainer tools" lists the modules. To run the same tests on Windows, run the command of that step in Git Bash from `tests/`. If you add a test module for a plugin script or a tool, add it to that step.

## Useful tests

Each test of this repository must be able to fail for a bug or for a bad change of behavior. A test that cannot fail in this way costs run time and review time, and it gives no signal. So do not add a test that only asserts that a constant has its literal value. Do not add a test that copies a text from a file and then finds the same text in that file. Test the code that uses the value instead. A test can pin a value that a user, a script, or a grader reads. Examples are a flag name and the form of a report line. Rule 8 of the skill [engineering-discipline](../essentials/dev-essentials/skills/engineering-discipline/SKILL.md) defines the same terms for the users of the plugins.
