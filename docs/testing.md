# Testing

The folder `tests/` holds the tests of this repository. It is outside every plugin folder, so Claude Code does not copy it into the plugin cache. The tests need Python 3, Git, and Claude Code (the `claude` command). The markdownlint test also needs Node.js 22 or later, because it runs `markdownlint-cli` through `npx`. Under WSL2, install Node.js in Linux. If the clone is in the Linux file system, the `npx` of a Windows install runs markdownlint in `C:\Windows`. This happens because `cmd.exe` cannot use a folder of the Linux file system as its current folder. So markdownlint finds no file. The test then skips. If the environment variable `CI` is `true`, the test fails. The YAML test of the eval cases also needs the Python package PyYAML. The step `Install PyYAML` of `.github/workflows/tests.yml` names the version.

To run all tests, run this command from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The command runs these parts:

- The tests of `check_report.py` (skill `bug-hunt`), `trim_report.py` (skill `trim-artifacts`), and `openbsd_lint.py` (skill `openbsd-style-docs`).
- The simple-english linter on every tracked `.md` file of the repository. A hit fails the test, unless `tests/simple-english-baseline.json` lists it. Each entry of that file gives the reason for the exception. A baseline entry without a hit also fails the test. The `excluded` key of that file lists folders that the test skips as a whole, each with a reason. An `excluded` folder with no tracked `.md` file also fails the test.
- markdownlint on every tracked `.md` file of the repository. The rules are in `.markdownlint.jsonc`. Each rule that the file turns off has a comment with the reason.
- `claude plugin validate --strict` on the marketplace and on each plugin.
- A budget for the always-on cost of each plugin, from `claude plugin details`. The always-on cost is the number of tokens that the names and descriptions of the skills, agents, and commands add to every session. The budgets are in `tests/test_plugin_cli.py`. Each budget is the most always-on tokens that `claude plugin details` can show in a signed-in session.
- The tests of the scripts of the `kb` plugin in `tests/test_kb_plugin.py`: the hook launcher, the setup check, and the hook entries. They need Bash and Git.
- A search of the plugin files for lines that ask the model to write out its reasoning. Such a line can make a model refuse the task.
- A search of the `README.md` files and the files in `docs/` for counts of hooks, skills, agents, and commands. Such a count goes stale.
- The tests of `tests/evals/compare_versions.py`. They use the result file in `tests/evals/fixtures/` and call no model.
- The static checks of every eval case in `tests/test_eval_cases.py`. They read the cases and call no model.
- The YAML test of the eval cases in `tests/test_eval_front_matter.py`. It parses the YAML of each `prompt.md`, `case.yaml`, and grader file of every plugin with PyYAML. `claude plugin eval` does not load a case with YAML that does not parse. If PyYAML is not installed, the test fails. It does not skip.
- The scaffold tests in `tests/test_eval_scaffolds.py`. They run each `scaffold.sh` of the eval cases in a temporary folder. They need Bash and Git. One test also builds a .NET solution, so it needs the .NET SDK 10 or newer and the .NET 10 runtime. If a tool is missing, the test skips. In CI, it fails.
- A version check for each plugin with a changed file. The `version` in its `plugin.json` must be higher than on the base branch.

The two linters read only the files that git tracks. If you add a new `.md` file, run `git add` on it before you run the tests.

The simple-english test first looks for the linter in the folder that the variable `SIMPLE_ENGLISH_DIR` names. This is the root of a clone of SimpleEnglish. Then it looks in the plugin cache. If no linter is found, the test skips. The baseline is for simple-english 2.1.1, so another version can report other hits.

The tests of `claude plugin validate` and `claude plugin details` give each call an empty, temporary configuration folder. They also remove the known environment variables that sign Claude Code in, for example `CLAUDE_CODE_OAUTH_TOKEN`. So these tests need no sign-in, and they do not load your installed plugins. If the `claude` command is not found, these tests skip.

With no sign-in, `claude plugin details` cannot count the tokens with the API. It shows an estimate instead: the number of characters divided by 4. A signed-in session shows the API count, which is higher. So the budget test multiplies the estimate by `SIGNED_IN_RATIO` before it compares the result with the budget. A new default model can count more tokens for the same text. The ratio also depends on the kind of text, because code and paths need more tokens for each character. The factor 1.5 was measured only on the current budgets, so a much smaller new budget needs a new measurement. In these cases, compare the output of `claude plugin details <plugin>` in a signed-in session with the estimate of the test, and raise `SIGNED_IN_RATIO`.

The version check compares the work tree with the merge base of `HEAD` and a base branch. In a CI run for a pull request, the base branch is the target branch of the pull request. On your machine, it is `origin/main`, or the branch that the variable `VERSION_BUMP_BASE` names. A CI run for a push to `main` skips the check, because the pull request already ran it.

The workflow `.github/workflows/tests.yml` runs the same command on each pull request and on each push to `main`. A new push to a pull request cancels the earlier run of that pull request. A run for a push to `main` is never cancelled while it runs. In CI, a missing linter or a missing `claude` command fails the run. CI installs the latest Claude Code with npm. CI also installs the .NET SDK 10 for the scaffold tests. CI also installs PyYAML for the YAML test of the eval cases. CI also fetches the full history of the repository, so that the version check finds the merge base. CI uses the latest release of SimpleEnglish, so the linter version does not fall behind. If a new linter version makes the lint test fail, treat it as a blocker. Open an issue and fix it at once.
