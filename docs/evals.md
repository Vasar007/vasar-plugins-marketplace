# Evals

This page is for a contributor who measures a change of a skill, an agent, or a command. It tells you how to run the eval cases and how to compare two commits. To write or change a case, read [Eval cases and graders](eval-cases.md).

An eval case is a prompt and its graders. A grader is a pass or fail test of a run. `claude plugin eval` runs the cases of a plugin and scores them. Each run calls a model on your account, so CI does not run the evals. The docs page [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) describes the case format.

## Choose the command

| Goal | Command |
| --- | --- |
| Compare a base commit with a head commit | `python3 tests/evals/compare_versions.py run` |
| Record the scores of one commit | `python3 tests/evals/compare_versions.py baseline` |
| Compare result files that you already have | `python3 tests/evals/compare_versions.py compare --base <files> --head <files>` |
| Run the trigger cases of `dev-essentials` | `claude plugin eval essentials/dev-essentials --tag triggers` |

Use the compare script for every plugin with dependencies and for every case that uses a stand-in plugin. The section [Dependencies and stand-ins](#dependencies-and-stand-ins) says why.

## Compare two commits

This example runs the suite of `dev-essentials` at `main` and at `HEAD`:

```bash
python3 tests/evals/compare_versions.py run --plugin essentials/dev-essentials --base main --head HEAD --model <model id> --judge-model <model id> --out <folder>
```

- Pass full model ids. The result files store them, because a comparison is valid only on the same models.
- Both sides run the cases of the head commit.
- The script writes `base.json`, `head.json`, and `report.md` into the `--out` folder. If the folder already holds a result file, the script stops.
- For a case that the report marks as unclear, the report prints the commands to run the case again.
- Run the script with `--help` for the rules of the verdict.

## Record one commit

To record the scores of one commit with no comparison, use `baseline`. This example records the trigger cases of `dotnet-backend-dev`:

```bash
python3 tests/evals/compare_versions.py baseline --plugin dotnet/dotnet-backend-dev --commit main --model <model id> --judge-model <model id> --tag triggers --out <folder>
```

The command writes `baseline.json` into the `--out` folder. Later, pass the file to `compare --base` or `compare --head`. `baseline` runs the cases of its own commit. So if two commits have different cases, do not compare their baseline files. If an eval fails or writes no case, `baseline` stops with exit code 2.

`run` and `baseline` both take `--keep-temp`, which keeps the run folders. Only `baseline` takes `--ablation none|with-without` (default `none`).

Do not commit a result file. It holds local temporary paths.

## Dependencies and stand-ins

`claude plugin eval` loads only the plugin under test. So a plugin with a dependency reports `dependency-unsatisfied` and does not load. The compare script fixes this in the copy of the plugin that it runs:

- It copies each plugin of `dependencies` in the manifest into `.deps/<name>`, from the same commit. A case lists these copies in the `plugins` field of its `prompt.md`.
- `--extra-dep <name>` copies a plugin that the manifest does not list. Repeat it for more plugins. The trigger cases of `doc-styles` use it for `dev-essentials`, because `doc-styles` must stay free of dependencies.
- It copies each folder of `tests/evals/stubs/` into `eval-stubs/`. These are stand-in plugins, for example of the GitHub server. A `run` uses the stand-ins of the head commit on both sides.

## Trigger cases

The trigger cases are in `evals/triggers/` of each plugin, with the tag `triggers`. A trigger case tests that the right unit starts for its words. A near-miss case tests that a unit does not start for the words of a neighbor unit. The trigger cases grant no shell tool, so they also run on native Windows.

To run the trigger cases of `dev-essentials`, run this from the repository root:

```bash
claude plugin eval essentials/dev-essentials --ablation none --trust-plugin --no-publish --model <model id> --judge-model <model id> --tag triggers
```

The run writes its results into `evals/results/` of the plugin. Git ignores this folder. To compare only the trigger cases at two commits, add `--tag triggers` to `compare_versions.py run`.

## Behavior suites

A behavior suite is a set of eval cases that runs a workflow skill on a small planted repository. The graders test the result: the files, the commits, the pushes, and the final message. Each suite is in `evals/` of its plugin, and the tag of its cases is the name of the suite.

| Plugin | Suite tags | Where it runs |
| --- | --- | --- |
| `dev-essentials` | The name of each skill or command with a folder in `evals/`, such as `review-loop`, `feature-pipeline`, and `merge-pr`. The tag `composers` covers `compose-pr`, `compose-task`, and `create-documentation` | WSL2 or Linux. `create-html-artifact` grants no shell tool, so it also runs on Windows |
| `dotnet-backend-dev` | `write-tests` | WSL2 or Linux |
| `doc-styles` | `style-compare-openbsd`, `style-compare-se`, `style-compare-both`, or `style-compare` for all three | WSL2 or Linux, because the hooks need `python3` and `node` |

A suite tag also selects the trigger cases of its skill. The tag `composers` selects only the behavior cases. The trigger cases of its skills carry the name of each skill as the tag.

A suite that grants `Bash` needs the sandbox of Claude Code, and native Windows has no sandbox. So run such a suite in WSL2 or on Linux. Run it through the compare script, because many cases use a stand-in or a dependency.

## Prepare WSL2

Do these steps one time before the first suite run:

1. Install `bubblewrap` and `socat`. The sandbox needs both.
2. For the `feature-pipeline` and `write-tests` suites, install the .NET SDK 10 outside your home folder. The sandbox cannot read your home folder, so an SDK in `~/.dotnet` does not work. On Ubuntu 26.04, the package `dotnet-sdk-10.0` works. The scaffolds also need `flock` from util-linux, which Ubuntu installs by default.
3. Set `TMPDIR` to a folder outside `/tmp`, `/var/tmp`, `/dev/shm`, and `/run/shm`, and make that folder. The sandbox denies these four folders, and the run folder follows `TMPDIR`. This is a bug of Claude Code ([anthropics/claude-code#104631](https://github.com/anthropics/claude-code/issues/104631)). The compare script stops with a message for such a `TMPDIR`.
4. For the `doc-styles` suites and probes, install Python 3 as `python3` and Node.js 22 or later as `node` in Linux. A Windows install of Node.js does not help, because WSL2 runs a Windows program only as `node.exe`.
5. Keep the clone for the eval runs in the Linux file system, for example in `~/src`. A file access below `/mnt/c` is slow. See [File storage and performance across file systems](https://learn.microsoft.com/en-us/windows/wsl/filesystems#file-storage-and-performance-across-file-systems).

A `wsl.exe` command from Windows starts in the current Windows folder. So start each such command in the Linux home folder. If a command such as `git clone` starts in a Windows folder, WSL also shows a performance tip in Windows.

- In Git Bash or PowerShell, write `wsl.exe --cd '~' -e bash -lc '<command>'`. Keep the quotes around `~`, because Git Bash changes a bare `~` to the Windows home folder.
- In `cmd.exe`, write `wsl.exe --cd ~ -e bash -lc "<command>"`.

To get a branch of a Windows clone into the Linux clone, use a git bundle:

```bash
# In Git Bash, in the Windows clone:
git bundle create //wsl.localhost/<distribution>/home/<user>/work.bundle main <branch>
# In the Linux clone:
git fetch ~/work.bundle '+refs/heads/*:refs/remotes/win/*'
```

The fetch puts the branch at `win/<branch>`. Pass that name to `--commit`, `--base`, or `--head`. Do not pass a plain name such as `main`, because the fetch does not move a local branch of the Linux clone. The scripts in `tools/wsl/` do these steps for you: see [Maintainer tools](tools.md#run-the-unit-suite-and-eval-runs-in-wsl2).

## Run a suite

This example runs the `review-loop` suite in WSL2:

```bash
export TMPDIR=$HOME/.cache/plugin-evals/tmp
mkdir -p "$TMPDIR"
python3 tests/evals/compare_versions.py baseline --plugin essentials/dev-essentials --commit <branch> --model <model id> --judge-model <model id> --scaffold --runs 3 --concurrency 3 --max-cost-usd <usd> --tag review-loop --out <folder> --allow-tools Bash Write Edit
```

- `--scaffold` makes each case build its repository with its `scaffold.sh`.
- `--allow-tools` grants the tools, because a run asks for no permission and grants no shell tool by default.
- If the shell does not find `claude`, pass its path with `--claude`.

## Run the main cases on a new model

When a new model comes out, [`CLAUDE.md`](../CLAUDE.md) asks for this run. The run shows which units start for the wrong request or fail on that model. It compares no two commits, so it needs no base.

The main cases are:

- Each trigger case of each plugin, with the tag `triggers`.
- One case of each main workflow: `rl-off-by-one`, `rirr-retry-limit`, `ppc-autonomous-push`, `fp-e2-fork-pr`, `it-no-worktree`, `ib-no-worktree`, and `bh-flow`.

Run each case one time with `baseline`. For a new eval agent or a new main model of sessions, pass the new model as `--model`. For a new judge, pass it as `--judge-model`. Give the other option the model of the last run:

```bash
python3 tests/evals/compare_versions.py baseline --plugin <plugin folder> --commit main --model <agent model id> --judge-model <judge model id> --scaffold --keep-temp --runs 1 --case <case> --out <results folder>/<plugin>-<case>
```

- A workflow case also needs `--allow-tools Bash Write Edit`.
- A trigger case of `doc-styles` also needs `--extra-dep dev-essentials`. See [Dependencies and stand-ins](#dependencies-and-stand-ins).
- Use one command for each run. `--max-cost-usd` is tested only before a run starts. So before each command, sum the spend with `python3 -I tools/eval_results.py spend --cap <USD> <results folder>/*/baseline.json`.
- Two plugins can have a trigger case with the same name. So name each `--out` folder by the plugin and the case.
- A case that scores 1.00 is done. Give a case with a lower score one more run.
- If a case fails two times, run it one time with the old model at the same Claude Code version. If that run fails too, the case is stale, and the model is not the cause.
- Before a verdict on a failed grader of a long run, replay it. See [Replay graders on kept runs](eval-cases.md#replay-graders-on-kept-runs).

The first model run was in November 2026. Its agent was a model of the Fable family, and its judge was a model of the Sonnet family. Each case scored 1.00.

| Part | Runs | Cost (USD) | Time of the runs |
| --- | --- | --- | --- |
| The trigger cases | 52 | 23.33 | About 17 minutes |
| The workflow cases | 7 | 19.37 | About 27 minutes |

A trigger run cost 0.21 to 1.35 USD. A workflow run cost 1.42 to 4.36 USD and took 73 to 431 seconds. Three of the workflow cases also ran with an agent of the Opus family at the same commit. Those runs cost about half as much, and each one took as long or longer.

## Probes

The probes are cheap cases that test the run environment, not a skill. They are in `evals/probes/` of each plugin, with the tag `probe`. Before the first paid suite run on a new machine, run them with the same command and `--tag probe`.

Run the probes of `doc-styles` in WSL2 or on Linux. On native Windows, its Python hooks gave no message in a run. Issue [#151](https://github.com/Vasar007/vasar-plugins-marketplace/issues/151) has the evidence.

## Clean the temp folder

The temp folder of your eval runs is the folder that `TMPDIR` names, for example `~/.cache/plugin-evals/tmp`. Nothing cleans this folder. `claude plugin eval` makes one `claude-eval-*` run folder in it for each run, and deletes it at the end of the run. With `--keep-temp`, it keeps the run folder and prints its path. A kept run folder holds the trace of the run in `out/trace.jsonl`. The kept folder is read-only, and its `sealed/` folder has no permissions, so a plain `rm -rf` cannot delete it.

The folder also collects leftovers: the run folders of stopped runs, the `compare-versions-*` copies of the compare script, and temporary files of .NET, NuGet, and Python. After some weeks, it can hold thousands of entries and several GB.

The steps below keep each entry that one of your notes names, and delete each other entry. A note is a `.md` or `.txt` file in which you wrote the path of a run folder, for example to read its trace later. The steps do not follow a link, and they read only UTF-8 text. A name that touches a letter, a digit, or `_` in a note does not count.

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
