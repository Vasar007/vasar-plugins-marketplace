# Maintainer tools

The folder `tools/` holds scripts for the maintainers of this repository. They help with the work around a pull request: a merge of `main` into an open branch, the results of eval runs, and the test runs and eval runs in WSL2. No plugin ships them. Claude Code copies only the folder of a plugin into the plugin cache, so a file outside the plugin folders does not reach the users. See [In-place and copied plugins](https://code.claude.com/docs/en/plugins/loading#in-place-and-copied-plugins).

Each Python script needs Python 3.7 or later and uses only the standard library. Run it with `python3 -I` from the repository root. Each script prints its full text with `--help`. Each shell script runs in Bash. The tests are in `tests/test_changelog_merge.py`, `tests/test_eval_results.py`, and `tests/test_tools_wsl.py`.

## Merge `main` into an open branch

A merge of `main` into an open branch gives the same conflicts each time: the top of `CHANGELOG.md`, its link lines, and the `version` in `plugin.json`. The script `tools/changelog_merge.py` writes these files new from the two sides of the merge. It stages nothing.

1. In the clone of the branch, run `git fetch origin` and then `git merge origin/main`.
2. If the branch adds a release section, run the subcommand `release`. Give each plugin of the release with its new version, and give the new release number:

   ```bash
   python3 -I tools/changelog_merge.py release --bump essentials/dev-essentials=3.25.0 --release 4.23.0
   ```

3. If the branch adds entries under `## [Unreleased]` and no release, run the subcommand `unreleased`:

   ```bash
   python3 -I tools/changelog_merge.py unreleased
   ```

4. If another file has a conflict in which both sides must stay, add `--keep-both <file>` for that file. The side of `main` comes first.
5. Read `git diff`. Then stage the files and commit the merge.

If `main` has entries under `## [Unreleased]`, the subcommand `release` stops. Only the pull request that merges next takes these entries into its release section. For that pull request, add `--absorb-unreleased`. The script also stops on a line that the branch added to `CHANGELOG.md` and that the result does not have. A line that starts with `STOP` gives the reason, and the script then changes no file.

## Read the results of eval runs

The script `tools/eval_results.py` reads the `baseline.json` files of `tests/evals/compare_versions.py` and the trace of a kept run. A `baseline.json` file has one key on each line, so `grep` gives wrong numbers. These are the subcommands:

- `runs <file>...` prints one line for each run: the score, the cost, the time, the run folder, and the failed graders.
- `spend --cap <USD> --rest <USD> <file>...` adds the cost of the files to the estimate of the runs to come. If the sum is over the cap, the exit code is 3. A queue of eval runs can call it before each run, because `--max-cost-usd` of a run is tested only before that run starts.
- `kept <file>...` prints one line for each kept run folder, for a note of the kept runs.
- `trace <trace.jsonl>` prints the text, the tool calls, and the tool results of a run in order. `--max-lines` limits the output.

## Run the unit suite and eval runs in WSL2

The whole unit suite passes only on Linux, and a suite that grants `Bash` runs only in WSL2 or on Linux. The scripts in `tools/wsl/` run both from Git Bash on Windows. They follow the rules of the section [Behavior suites](evals.md#behavior-suites):

- Each `wsl.exe` call starts in the Linux home folder, so no command starts on a Windows drive.
- No Linux command reads a path below `/mnt/c`. A branch goes to WSL2 as a git bundle, and a result comes back by a copy from Git Bash.
- The Linux part of each script goes to WSL2 through a pipe before each run, so WSL2 never holds an old copy.

These scripts keep their files in one folder of the Linux home folder: `~/.cache/marketplace-tools`. The variable `TOOLS_DIR` changes this folder, relative to the home folder. The variable `WSL_DISTRO` names the distribution (default `Ubuntu`).

To run the whole unit suite of a committed branch, run this in Git Bash:

```bash
bash tools/wsl/unit-tests.sh /c/path/to/clone my-branch
```

The script clones the branch into a new folder and runs `python3 -m unittest discover -s tests -v` there. It uses the newest release of the simple-english linter, or the release of `--linter-tag`. The run gets its own `/tmp/plugin-evals` through a private mount, so it does not touch the NuGet folder of an active eval run. The exit code is the exit code of the suite.

To run one command of `tests/evals/compare_versions.py`, run this in Git Bash:

```bash
bash tools/wsl/run-eval.sh /c/path/to/clone my-branch results/head baseline --plugin essentials/dev-essentials --commit HEAD --model <model id> --judge-model <model id> --case <case> --scaffold --keep-temp
```

The third argument is the result folder on Windows. The script adds `--out` and `--claude` itself. The runs must use the claude.ai plan, not API billing. So the script stops on a set `ANTHROPIC_API_KEY`, and on another sign-in than claude.ai. A lock lets only one run use the eval clone at a time. A run also waits until no unit suite and no other eval run is active, unless you give `--no-wait`. The eval clone is `~/.cache/marketplace-tools/eval-clone`, or the Linux path of `--clone`.

To free space, delete the folders `bundles`, `out`, and `test-clones` of the tools folder. Keep `nuget-private`, because it holds the NuGet packages of the unit suite. The section [Clean the temp folder](evals.md#clean-the-temp-folder) says how to clean the temp folder of the eval runs.
