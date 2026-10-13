# Inputs and meta-plan

The orchestrator reads this file at step 0. After the user's OK, the session progress file holds the approved values, so later steps do not need this file. Rule and step numbers refer to `SKILL.md`.

## Inputs

The user gives the inputs as arguments or answers the step-0 questions.

| Input | Argument | Default |
| --- | --- | --- |
| Repository path | first argument | If the current working directory is a git repository, that directory |
| Project name | `--name` | The folder name of the repository |
| GitHub repository | `--github` | None. Ask. Propose `owner/repo` from the `origin` remote, and say that the remote can hold an old name. |
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
| Experiments | `--experiments` | Default: ask at step 0, and propose `yes`. `yes`: agents can build, restore, test, and run code on snapshot copies in their work folders. `no`: agents only read code. |
| Services for experiments | step-0 answer | None. Examples: a database server, a container runtime. |
| Pause points | `--stop-after` | None. See [pauses.md](pauses.md). |
| Resume and start times | `--resume-at`, `--start-at` | None |
| Hunter model and effort | `--hunter-model`, `--hunter-effort` | `fable`, `max` |
| Verifier model and effort | `--verifier-model`, `--verifier-effort` | `opus`, `xhigh` |
| Auditor model and effort | `--auditor-model`, `--auditor-effort` | `opus`, `xhigh` |

Do not guess the report folder. Ask for it. Do not take the GitHub repository from the
remote without the user's OK. GitHub redirects a renamed repository, so the remote can show
an old name.

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
2. Areas: a table with the number, name, paths, file count, size, and order.
3. Excluded paths, each with a reason, for example vendored or generated code.
4. Agents: a table with the model and effort of each role. Say in one sentence that the OK approves the Fable dispatches. If the `Agent` tool has no `effort` parameter, say that the agents run at the effort in their agent files.
5. Files: the report path, the run context file, the final summary file, the artifacts folder, the progress file names, and the scratch folder. If the report folder is inside the analyzed repository, say so here. The run then creates new files in the project tree, and only there.
6. Verification: the split threshold and the split rule of step 4.
7. Base: the base branch and its source. For a local base, give the date of its last commit. If the analyzed commit is the base, or the base is `none`, say so.
8. Experiments: whether agents can build, restore, test, and run code on snapshot copies, and which services, for example a database, are available.
9. Pauses: the pause points, the resume times, and the start time, or "None".
10. Run format: the orchestrator checks only the structure of the output (rule 3), and the verifiers and the auditor check the content. Chat gets at most one status line for each step and one final report (rule 8). Say in one sentence that the OK also accepts this run format.
11. Plain English: whether `simple-english` is installed, or the fallback is used.
12. Cleanup: the list of what step 6 deletes and what it keeps.
13. Questions: a numbered list. Always ask the user to approve the analyzed commit, the base and its source, and the GitHub repository name. Also ask for the bug label and the other known-bug sources, the experiments and services, and the pause points. Then add each question that blocks the run.

## Questions that block the run

Ask a question in these cases:

- The report folder is missing, or the report file exists.
- The report folder already holds a `bug-hunt-artifacts` folder or a `_bug-hunt-progress-*.md` file, and no resume applies. A new run then writes into the files of the old run.
- The run context file or the final summary file exists, and no resume applies. Offer to reuse the context file, or to use the dated names `bug-hunt-context-<YYYY-MM-DD>.md` and `bug-hunt-final-summary-<YYYY-MM-DD>.md`.
- The base branch is unknown, or the GitHub repository is not approved.
- Fable is not available, or a plugin agent type for the hunter, verifier, or auditor is not available.
- There is no known-issue source.

## Session progress file

After the user's OK, write `_bug-hunt-session-progress.md` in the report folder (rule 6). Record these values:

- The inputs, the commit SHAs, the base source, and the scratch folder.
- The approved models and effort levels.
- The output of `git -C "<repo>" --no-optional-locks status --porcelain`. Step 6 compares it with a new output.
- The areas, the experiments and services, and the pause points and times.
- The approval itself.
