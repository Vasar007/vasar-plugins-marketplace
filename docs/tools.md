# Maintainer tools

The folder `tools/` holds scripts for the maintainers of this repository. They help with the work around a pull request: a merge of `main` into an open branch, the results of eval runs, and the test runs and eval runs in WSL2. No plugin ships them. Claude Code copies only the folder of a plugin into the plugin cache, so no plugin cache gets a file outside the plugin folders. See [In-place and copied plugins](https://code.claude.com/docs/en/plugins/loading#in-place-and-copied-plugins).

Each Python script needs Python 3.7 or later and uses only the standard library. Run it with `python3 -I` from the repository root. Each shell script runs in Bash. With `--help`, each script that you start prints its usage text: its options, its exit codes, and the cases in which it refuses to run. The tests are in `tests/test_changelog_merge.py`, `tests/test_eval_results.py`, and `tests/test_tools_wsl.py`.

## Merge `main` into an open branch

A merge of `main` into an open branch gives the same conflicts each time: the top of `CHANGELOG.md`, its link lines, and the `version` in `plugin.json`. The script `tools/changelog_merge.py` writes these files new from the two sides of the merge. It stages nothing.

1. In the clone of the branch, run `git fetch origin` and then `git merge --no-commit origin/main`. With `--no-commit`, a merge with no conflict also stays in progress, so that the script can run.
2. If the branch adds a release section, run the subcommand `release`. Give each plugin of the release with its new version, and give the new release number:

   ```bash
   python3 -I tools/changelog_merge.py release --bump essentials/dev-essentials=3.25.0 --release 4.23.0
   ```

3. If the branch adds entries under `## [Unreleased]` and no release, run the subcommand `unreleased`:

   ```bash
   python3 -I tools/changelog_merge.py unreleased
   ```

4. If another file has a conflict in which both sides must stay, add `--keep-both <file>` for that file. Give the file as a path from the top folder of the repository. The side of `main` comes first.
5. Read `git diff`. Then stage the files and commit the merge.

If `main` has entries under `## [Unreleased]`, the subcommand `release` stops. Only the pull request that merges next takes these entries into its release section. For that pull request, add `--absorb-unreleased`. The subcommand `release` stops for a branch with no new release section since the merge base. Two open branches can take the same heading: the same plugin versions, release number, and date. The other branch can merge first. Then `main` has the top heading of the branch too. That section of the branch is still a new release, so the script puts it on top with the new numbers. The script leaves out each bullet that `main` added since the merge base. If `main` already has each bullet of that section, the script stops. That happens, for example, after a squash merge of the same branch. Then the branch has no entry of its own. If the branch has a change that `main` does not have, stop the merge with `git merge --abort`. Add an entry for that change to the section, commit, and merge again. With the same heading, the script also stops in two more cases. In the first case, both sides have a bullet with other indented lines. In the second case, the section has no bullet that starts with a dash. The script also stops on a line that the branch added to `CHANGELOG.md` and that the result does not have. The subcommand `unreleased` stops on an entry of the merge base under `## [Unreleased]` that the branch changed or removed. Then merge `CHANGELOG.md` by hand. It also stops on an entry of both sides with one first line but other indented lines. A line that a side removed or changed since the merge base can come back in the result. A line that a side added can go. In each case, the script stops too. With no merge in progress, the script stops too. It also stops for a `--theirs` that is not the commit that merges in. The last stop is for a `plugin.json` in which both sides changed lines other than the version. A line that starts with `STOP` gives the reason, and the script then changes no file. If the script cannot write a file, the exit code is 1, and the `RESULT` line gives the count of the written files.

## Read the results of eval runs

The script `tools/eval_results.py` reads the `baseline.json` files of `tests/evals/compare_versions.py` and the trace of a kept run. A `baseline.json` file has one key on each line, so `grep` gives wrong numbers. These are the subcommands:

- `runs <file>...` prints one line for each run: the score, the cost, the time, the run folder, and the failed graders. A `PARTIAL` line marks a file whose suite did not finish, and `NO RUN` marks a case with no run.
- `spend --cap <USD> --rest <USD> <file>...` adds the cost of the files to the estimate of the runs to come. If the sum is over the cap, the exit code is 3. If a cost, `--cap`, or `--rest` is not a number of 0 or more, the exit code is 2. A queue of eval runs can call it before each run, because `--max-cost-usd` of a run is tested only before that run starts.
- `kept <file>...` prints one line for each kept run folder, for a note of the kept runs.
- `trace <trace.jsonl>` prints the text, the tool calls, and the tool results of a run in order. By default, it shows 80 lines. It cuts a text or an input at 250 characters, and a result at 125. `--max-lines` and `--limit` change these numbers.

## Run the unit suite and eval runs in WSL2

The whole unit suite passes only on Linux, and a suite that grants `Bash` runs only in WSL2 or on Linux. The scripts in `tools/wsl/` run both from Git Bash on Windows. They follow the rules of the section [Behavior suites](evals.md#behavior-suites):

- Each `wsl.exe` call starts in the Linux home folder, so no command starts on a Windows drive.
- No Linux command reads a path below `/mnt/c`. A branch goes to WSL2 as a git bundle, and a result comes back by a copy from Git Bash.
- The Linux part of each script goes to WSL2 through a pipe before each run, so WSL2 never holds an old copy.

Prepare WSL2 first:

1. Install a WSL2 distribution. If its name is not `Ubuntu`, set the variable `WSL_DISTRO` to its name. The command `wsl.exe -l -q` lists the names.
2. In Linux, install Git and Python 3 as `python3`. The scripts also use `flock` and `unshare` from util-linux. Ubuntu installs both by default.
3. For the unit suite, install the tools that [Testing](testing.md) names: PyYAML, Node.js 22 or later, the .NET SDK 10 or newer, and Claude Code. Without PyYAML, a test fails. Without one of the other tools, some tests skip.
4. For `run-eval.sh`, install Claude Code inside the distribution, not on Windows. The script looks for `~/.local/bin/claude` first, and then for `claude` on the `PATH`. It stops on a `claude` below `/mnt`, because that is a Windows install. See [Install in WSL](https://code.claude.com/docs/en/setup#install-in-wsl).
5. For `run-eval.sh`, run `claude auth login` in Linux and sign in with your claude.ai account. Do not pass `--console`, because that sign-in uses API billing. Then `claude auth status` must show `"authMethod": "claude.ai"`. Do not set `ANTHROPIC_API_KEY` in Linux.
6. For `run-eval.sh`, also install the tools that the list in [Behavior suites](evals.md#behavior-suites) names for your suite, for example `bubblewrap` and `socat`. The script sets `TMPDIR` itself, and it keeps the eval clone in the Linux file system.
7. Make sure that Linux has network access. With no `--linter-tag`, `unit-tests.sh` reads the release tags of the linter from GitHub. It also clones each new linter release from there.

These scripts keep their files in one folder of the Linux home folder: `~/.cache/marketplace-tools`. The variable `TOOLS_DIR` changes this folder, relative to the home folder. The runs use `~/.cache/plugin-evals/tmp` as the temp folder. The variable `WSL_DISTRO` names the distribution (default `Ubuntu`). The variable `WSL_UNC_ROOT` gives the Windows path of the root folder of the distribution (default `//wsl.localhost/<distribution>`).

To run the whole unit suite of a committed branch, run this in Git Bash:

```bash
bash tools/wsl/unit-tests.sh /c/path/to/clone my-branch
```

The script clones the branch into a new folder and runs `python3 -m unittest discover -s tests -v` there. It uses the newest release of the simple-english linter, or the release of `--linter-tag`. The run gets its own `/tmp/plugin-evals` through a private mount, so it does not touch the NuGet folder of an active eval run. The mount needs `unshare -r -m`. If Linux refuses it, the run fails. Then pass `--no-private-mount`, but only while no eval run is active. The exit code is the exit code of the suite.

To run one command of `tests/evals/compare_versions.py`, run this in Git Bash:

```bash
bash tools/wsl/run-eval.sh /c/path/to/clone my-branch results/head baseline --plugin essentials/dev-essentials --commit HEAD --model <model id> --judge-model <model id> --case <case> --scaffold --keep-temp
```

The third argument is the result folder on Windows. It must be empty or new. The script adds `--out` and `--claude` itself. The runs must use the claude.ai plan, not API billing. So the script stops on a set `ANTHROPIC_API_KEY`, and on another sign-in than claude.ai. A lock lets only one run use the eval clone at a time. A run also waits until no unit suite and no other eval run is active, unless you give `--no-wait`. The eval clone is `~/.cache/marketplace-tools/eval-clone`, or the Linux path of `--clone`.

To free space, delete the folders `bundles`, `out`, and `test-clones` of the tools folder, and each `simple-english-<tag>` folder of an old linter release. If no eval run is active, you can also delete `eval-clone`. The next run makes it again. Keep `nuget-private`, because it holds the NuGet packages of the unit suite. The section [Clean the temp folder](evals.md#clean-the-temp-folder) says how to clean the temp folder of the eval runs.
