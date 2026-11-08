# Inputs and meta-plan

The orchestrator reads this file at step 0 and follows "Step 0 procedure". After the OK of the user, or the default approval, the session progress file holds the approved values. Later steps do not need this file. A resume reads item 2 again only to pick a new scratch folder. Rule and step numbers refer to `SKILL.md`. Item numbers refer to "Step 0 procedure".

## Step 0 procedure

1. Resolve the inputs from the arguments and the defaults. Do not guess the report folder. Take the GitHub repository as the Inputs table says. This is the documented exception in `dev-essentials:github-mcp-conventions` Rule 1. Find out whether the report folder exists. If it is missing, ask. Else list the files in it that start with `bug-hunt` or `_bug-hunt`.
2. Pick the scratch folder. If the environment gives a session scratchpad directory, use it with a `bug-hunt` subfolder. Else, create a new folder in the system temp folder, for example `bug-hunt-<YYYYMMDD-HHMM>`. The scratch folder must not be inside the project or the report folder.
3. Dispatch the scoping helper. It proposes the areas from the tree of the analyzed commit.
4. Look for `simple-english:simple-english` in the list of available skills.
5. Write the meta-plan in chat, with every part that "Parts of the meta-plan" lists.
6. Ask only questions that block the run.
7. Without `--interactive`, and with no question that blocks the run, continue. The meta-plan in chat states the run. With `--interactive`, wait for the user's explicit OK. If the user changes a value, apply the change. If the change raises a new question, show the meta-plan again. Else do not show it again.
8. After the OK, or after item 7 without `--interactive`, do this. Write `_bug-hunt-session-progress.md` in the report folder, with the values that "Session progress file" lists. If a start time is set, schedule the start as [pauses.md](pauses.md) says, and end the turn.

## Inputs

The user gives the inputs as arguments or answers the step-0 questions.

| Input | Argument | Default |
| --- | --- | --- |
| Repository path | first argument | If the current working directory is a git repository, that directory |
| Project name | `--name` | The folder name of the repository |
| GitHub repository | `--github` | Without `--interactive`: `owner/repo` from the `origin` remote. Mark it in the Scope section as `Not confirmed: taken from the remote`. With `--interactive`: ask, propose `owner/repo` from the `origin` remote, and say that the remote can hold an old name. |
| Analyzed commit | `--ref` | `HEAD` of the repository. The orchestrator resolves it to a commit SHA. |
| Base branch | `--base` | The default branch of `origin`, as a branch name without the remote prefix (`main`, not `origin/main`). If git cannot tell, ask. `none` turns off the base comparison. |
| Base source | `--base-from` | Default: `local`. `local`: the local branch. `remote`: a fresh clone of the branch from the remote into the scratch folder. |
| Report folder | `--report-dir` | None. Ask. |
| Report file | `--report-file` | `bug-hunt-report.md`. If that file exists, propose `bug-hunt-report-<YYYY-MM-DD>.md`. |
| Notes files with known bugs | `--known`, repeatable | None |
| Label of bug issues | `--bug-label` | `bug` |
| Context file for orientation | `--context` | None |
| Role of the user | `--role` | "Not stated" |
| Number of areas | `--areas` | 5 |
| Split threshold for pass 1 | `--split-threshold` | 40 findings |
| Experiments | `--experiments` | `yes` without `--interactive`. With `--interactive`, ask at step 0, and propose `yes`. `yes`: agents can build, restore, test, and run code on snapshot copies in their work folders. `no`: agents only read code. |
| Services for experiments | step-0 answer | None. Examples: a database server, a container runtime. |
| Pause points | `--stop-after` | None. See [pauses.md](pauses.md). |
| Resume and start times | `--resume-at`, `--start-at` | None |
| Hunter model and effort | `--hunter-model`, `--hunter-effort` | `fable`, `max` |
| Verifier model and effort | `--verifier-model`, `--verifier-effort` | `opus`, `xhigh` |
| Auditor model and effort | `--auditor-model`, `--auditor-effort` | `opus`, `xhigh` |

The context file is for orientation only. Do not read other files in its folder. If an agent
needs one of them, the agent reads it.

## Defaults from git

For the defaults, use only these light read-only calls:

- `git -C "<repo>" rev-parse --verify "<ref>^{commit}"`
- `git -C "<repo>" rev-parse --abbrev-ref origin/HEAD`. It prints `origin/<branch>`. Remove the `origin/` prefix, because `{BASE}` is the branch name alone.
- `git -C "<repo>" remote get-url origin`
- `git -C "<repo>" log -1 --format=%cs "<base>"`, for the date of the local base.

## Parts of the meta-plan

1. Inputs: a table with each value and where it came from (argument or default).
2. Areas: a table with the number, name, paths, file count, and size, in search order. Number the areas in the approved search order, so that area 1 is searched first. If the user changes the order, renumber the areas.
3. Excluded paths, each with a reason, for example vendored or generated code.
4. Agents: a table with the model and effort of each role. Say in one sentence how the Fable dispatches are approved (rule 7). If the `Agent` tool has no `effort` parameter, say that the agents run at the effort in their agent files.
5. Files: the report path, the run context file, the final summary file, the artifacts folder, the progress file names, and the scratch folder. If the report folder is inside the analyzed repository, say so here. The run then creates new files in the project tree, and only there.
6. Verification: the split threshold and the split rule of step 4.
7. Base: the base branch and its source. For a local base, give the date of its last commit. If the analyzed commit is the base, or the base is `none`, say so.
8. Experiments: whether agents can build, restore, test, and run code on snapshot copies, and which services, for example a database, are available.
9. Pauses: the pause points, the resume times, and the start time, or "None".
10. Run format: the orchestrator checks only the structure of the output (rule 3), and the verifiers and the auditor check the content. Chat gets at most one status line for each step and one final report (rule 8). Say in one sentence how this run format is accepted (rule 8).
11. Plain English: whether `simple-english` is installed, or the fallback is used.
12. Cleanup: the list of what step 6 deletes and what it keeps.
13. Questions: a numbered list. With `--interactive`, always ask the user to approve the analyzed commit, the base and its source, and the GitHub repository name. Also ask for the bug label, the other known-bug sources, the experiments and services, and the pause points. Without `--interactive`, list these values with their defaults instead. In both modes, add each question that blocks the run.

## Questions that block the run

Ask a question in these cases:

- The report folder is missing, or the report file exists.
- The report folder already holds a `bug-hunt-artifacts` folder or a `_bug-hunt-progress-*.md` file, and no resume applies. A new run then writes into the files of the old run.
- The run context file or the final summary file exists, and no resume applies. Offer to reuse the context file, or to use the dated names `bug-hunt-context-<YYYY-MM-DD>.md` and `bug-hunt-final-summary-<YYYY-MM-DD>.md`.
- The base branch is unknown. With `--interactive`, also: the GitHub repository is not approved.
- The model or the plugin agent type of the hunter, the verifier, or the auditor is not available.
- There is no known-issue source.

## Session progress file

At item 8 of "Step 0 procedure", write `_bug-hunt-session-progress.md` in the report folder (rule 6). Record these values:

- The inputs, the commit SHAs, the base source, and the scratch folder.
- The approved models and effort levels.
- The output of `git -C "<repo>" --no-optional-locks status --porcelain`. Step 6 compares it with a new output.
- The areas, the experiments and services, and the pause points and times.
- The approval itself, and whether the user or the default gave it.
