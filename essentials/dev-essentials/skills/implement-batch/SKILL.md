---
name: implement-batch
description: Implement N related tasks in one branch or worktree. Plan and review each task, then make one squashed commit per task and one final review across all tasks.
argument-hint: <parent issue reference, or an explicit list of N tasks> [--base=<branch>] [--worktree=<branch-ref>] [--no-worktree] [--plan-dir=<path>] [--rounds=N] [--mode interactive|partial|full]
---

# Implement Batch (N tasks, N commits + at most 1 final-review commit)

## Division of labor in this skill family

- `dev-essentials:implement` runs the tasks of an existing plan file, with no research and no review loop.
- `dev-essentials:opsx-implement` implements phases of an existing OpenSpec change, with no research and no review.
- `dev-essentials:research-implement-review-report` (RIRR) works one task: research, a plan, the implementation, a review loop, and a report.
- `dev-essentials:implement-task` wraps RIRR for one task. It adds a sweep of extra context first and a `/simplify` commit at the end.
- `dev-essentials:implement-batch` works N related tasks in one branch: one squashed commit for each task, then one final review across the tasks.
- `dev-essentials:feature-pipeline` runs one task end-to-end in an isolated git worktree. The task is a tracked task of the task provider (for example, GitHub Issues or Jira), or a plain request. Subagents run its stages from the requirements to the reviews, the session pushes and opens the PR, and it has its own approval gates.

The configured branch prefix is `${user_config.branch_prefix}`. The notes folder is `${user_config.notes_dir}`. Set both with `/plugin configure` (see `plugin.json`). If a value still shows as a `${...}` placeholder, no value is saved. Then the configured branch prefix is empty, and the notes folder is `Notes`.

**Arguments**: $ARGUMENTS

- Format: `<parent issue reference, or an explicit list of N tasks> [options]`
- Examples (no value in them is fixed behavior):
  - `Issue 1469733 — implement all its sub-issues --base=release/2.0 --worktree=jdoe/tasks/1469733-custom-retention-enhancements`
  - `Plans/custom-retention-plan.md — implement every task in this plan --base=release/2.0` (the plan file is in the notes folder)
  - `1) add the retention option 2) wire it through the scheduler 3) cover it with tests --base=release/1.0 --worktree=jdoe/tasks/987654-retention`
- **N comes from the input of the user**: the list, the plan file, or the sub-issues of the parent. Never assume a count, and never drop or add a task silently.
- If $ARGUMENTS is empty, use the **AskUserQuestion** tool to ask which tasks to implement.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`, `master`, or `develop`. |
| `--worktree=<branch-ref>` | ask or derive | The branch ref that all N tasks share. Use the ref that this flag or the prose of $ARGUMENTS names, verbatim. Else build `<prefix>/<parent-type>s/<parent-ID>-<slug>`. Take the prefix from the first of these that gives one: a branch-naming rule in the `CLAUDE.md` of the repo, the configured branch prefix, a branch-naming rule in the `CLAUDE.md` of the user. If none gives a prefix, **ask once**. With `--no-worktree`, the ref names only the branch that Step 1 creates, so resolve it only then. |
| `--no-worktree` | off | Make no worktree, and work on the current branch in the current folder. Step 1 says what the run does on the default branch, the base branch, or a detached HEAD. |
| `--plan-dir=<path>` | `Plans/` in the notes folder | The folder inside the worktree for the plan files. A plan location that the repo documents wins. The plan files stay out of every commit (see "Guardrails"). |
| `--rounds=<N>` | `2` | Review-loop cycles, passed as `--rounds` to every loop: the plan loops, the code loops, and the final loop. |
| `--mode interactive\|partial\|full` | `partial` | The work mode. `dev-essentials:work-modes` defines the modes, and the gate table in "Autonomy" says what each mode does here. |

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the three modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Before Step 0: the GitHub repository of the pull request | Find it at the final gate, before its question | Same | Find it now, as "The repository" in `references/finish.md` of `dev-essentials:work-modes` says. When that file says to do no step, skip this row |
| Step 0: the sub-issue list of a parent issue | State it, and start | Wait for approval | Same as partial |
| Step 1: `--no-worktree` on the default branch, the base branch, or a detached HEAD | Ask for a branch name. On a branch, also offer a yes to work on it, with local commits and no finish step | Same | Create the branch of the `--worktree` row, and name it in the final report |
| Step 2: open decisions and unsure plan findings | Ask them all in one batch | Ask | Decide, and write each one into its plan |
| Steps 2 to 4: review loops | See "Review-loop configuration" | Same | Same |
| Steps 3.6 and 4.4: the squash script refuses (exit code 3) or cannot run (exit code 2, or no `RESULT` and no `OLD HEAD` line) | Stop and ask | Same | Skip the squash, and report it |
| Steps 3.6 and 4.4: the squash script fails (`RESULT: FAILED`, or an `OLD HEAD` line and no `RESULT` line) | Stop and ask | Same | Stop and ask |
| Step 6: push, pull request, and merge | Ask one question after the report | Same | No stop. A failed step ends the run with a report |
| Fable on the own initiative of the agent | Move up by the model ladder, and name the step in the final report | Ask before each Fable dispatch | Same as partial |

When this workflow passes its mode on, it does not pass the interactive mode to the Step 2 plan-review loops (see "Review-loop configuration").

## Subagent dispatch

Read `dev-essentials:subagent-orchestration` before the first dispatch. Its rules apply to every dispatch. A bare "Rule N" in this file is one of them. This skill adds these:

- **Dispatch by the tests** of Rule 1. The planners of Step 2 pass the parallel test. The implementer of each task passes the context test, because N tasks fill the main context. The review loops review each diff, so the orchestrating session reviews none. It does the git bookkeeping (commits, squashes, SHA records), a small lookup, and the talk with the user. Each brief asks for a short structured report (verdicts, `file:line` anchors, commands and results), never pasted diffs or file dumps.
- **Models**: Opus plans and reviews, and Sonnet implements and fixes. A task that the plan gives as an explicit 1-2-3 edit list uses Haiku. A code search that a test of Rule 1 sends to a subagent uses Haiku, through `dev-essentials:code-locator`. This line is the one home of these models, and the steps below name only the role. Haiku can do a mechanical extraction, such as the list of sub-issues. All follow "Model selection" in `dev-essentials:subagent-orchestration`.
- **Effort**: pass `effort` on each dispatch of a general agent type. The planner of Step 2: `high`, or `xhigh` for a large plan or a change on the critical path. The implementer of Step 3: `high`. For a task that the plan gives with its exact files and edits, use `medium`. An edit-list implementer and a mechanical extraction: `low`. `dev-essentials:review-loop` sets the effort of the reviewer and of a fixer subagent with its `--reviewer-effort` and `--fixer-effort` options. This line is the one home of these effort levels.
- **Parallel where safe, sequential where not.** All N tasks share one worktree. Two dispatches can run at the same time only under two rules. Each one writes its own path. Neither one runs a git command that changes the worktree, the index, or the history. Such commands are `add`, `commit`, `checkout`, `reset`, and branch operations, but not `log`, `show`, or `diff`.
  - The Step 2 planners qualify. Each one writes only its own `<--plan-dir>/<task-slug>-plan.md`, and uses git only to read (for example for `file:line` anchors). Dispatch them in parallel, and write both rules into every planner brief.
  - The implementation does not qualify. The Step 3 implementers edit shared product and test files, and the session commits their work. So implement and review **strictly one task at a time**. The same holds for the Step 2 plan-review loops and the Step 4 final loop, because this session runs each loop itself.
- A bounded dispatch does the work itself, and does not delegate it again (Rule 7). Examples: the plan of one task, one implementation, or one fix.

## Guardrails

- **One task per commit** in the final stack. Do not merge two tasks into one commit or split one task across two, unless the user asks.
- **Plan files stay out of commits**. Never stage a plan file of this run, and name the plan paths in the final report. A later reader of the history does not have the plans (`dev-essentials:engineering-discipline` Rule 3). Also, a repo can ignore the plan folder, and then `git add` of a plan file fails.
- **Own every red signal** from each build or test run in this session (`dev-essentials:engineering-discipline` Rule 1). Never call one "pre-existing", and do not search the history to find out whether it predates the batch.
- **Do not improvise.** Ask the user about an unclear plan item, an ambiguous review finding, or a task that is bigger than its plan. Do not guess. In the full mode, decide as `dev-essentials:work-modes` says.
- The plan files are the source of truth. Keep them up to date as tasks complete.

## Progress tracking for the user

Keep a task list with one entry for each task and one for the final review, and update it. Use `TodoWrite`, or `TaskCreate`, `TaskUpdate`, and `TaskList`, whichever this session has. The list is for the user only, never for coordination between subagents.

## Steps

A request to finish an earlier run of this skill goes straight to Step 6, as "Resume" in its file `finish.md` says.

### Step 0 — Resolve the batch

1. Find the task list, and so **N**:
   - An explicit list in $ARGUMENTS: use it verbatim, in the given order.
   - A plan file path: use the task or phase list of the plan.
   - A parent issue reference: dispatch a subagent that lists its sub-issues from the tracker (Rule 4, and `dev-essentials:github-mcp-conventions` for GitHub). State the list and its count in one status line, and repeat them in the final report. Outside the interactive mode, start the work. In the interactive mode, **show the list to the user for approval** before the work starts. An explicit list needs no approval.
2. Resolve `--base` and `--worktree` as the Options table says.
3. If a material fact is missing or unclear, ask with the **AskUserQuestion** tool before any work. Examples: which tasks, which branch, the worktree name, or the intended order and dependencies. If nothing is unclear, start the work.
4. Fix the **order** of implementation: the order of the user, else the dependency order of the plan. State the order in one line.

### Step 1 — Worktree setup

Without `--no-worktree`, create the worktree from the Step 0 base branch with `dev-essentials:git-worktree-management`, and run its post-create bootstrap. Record the absolute worktree path.

With `--no-worktree`, make no worktree. Record the path that `git rev-parse --show-toplevel` prints as the worktree path, and use it wherever this file names the worktree. Then run `git -C "<worktree>" status --porcelain --untracked-files=no`. If it prints a line, stop before any work, in every mode. Name each changed file, and ask the user to commit or stash it (hard stop 1 of `dev-essentials:work-modes`). Else a change in a file of a task goes into the task commit. Then record the output of `git -C "<worktree>" ls-files --others --exclude-standard`. Each file in it is a file of the user with no other copy. Never write, stage, or delete one of them. A build or a test run of a task can still rewrite its own output in this list. An example is a compiled file that `.gitignore` does not name. If a task needs one, ask the user first (hard stop 1 of `dev-essentials:work-modes`). Find the default branch with `git -C "<worktree>" symbolic-ref --quiet --short refs/remotes/origin/HEAD`, and take the name after `origin/`. If the ref does not exist, take the name from the `ref: refs/heads/<name>` line of `git -C "<worktree>" ls-remote --symref origin HEAD`. If that also gives no name, treat `main` or `master` as the default branch. Then run `git -C "<worktree>" branch --show-current`:

- If it prints the default branch, the Step 0 base branch, or nothing (a detached HEAD), do not commit there. Do what the `--no-worktree` row of "Autonomy" says. If the user says yes to work on that branch, make local commits only, and do no step of `finish.md`. For a new branch, run `git -C "<worktree>" switch -c <branch>`. If a branch of that name exists, ask the user (hard stop 6 of `dev-essentials:work-modes`).
- If it prints another branch, work on that branch, and create no branch. If the request names another branch ref, ask the user first (hard stop 6 of `dev-essentials:work-modes`).

Then, unless the user said yes to work on the current branch, run `git -C "<worktree>" rev-list --count origin/<base>..HEAD`, with the Step 0 base. If it fails, or prints more than 0, the pull request can take commits that no review loop of this run covers. Outside the full mode, list the commits or the error, and ask the user (hard stop 6 of `dev-essentials:work-modes`). In the full mode, go on. List the commits or the error in the final report as the reason that the run does no step of `finish.md`.

Each write-capable dispatch from here on carries the worktree path (Rule 6), and each git call uses `git -C "<abs worktree path>"`.

Then record `BATCH_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.

### Step 2 — Plan every task

Dispatch planners in parallel, one for each task. Each one writes `<--plan-dir>/<task-slug>-plan.md` inside the worktree. A plan holds the scope of the task, the files that it touches, and the patterns that it must follow (with `file:line` anchors). It also holds its verification commands and each open decision. An open decision is a critical decision that the task, the code, and the documentation do not settle (`dev-essentials:engineering-discipline` Rule 2).

Then, for each plan, run `dev-essentials:review-loop` with `target=spec <plan path>`, and fix the plan as the loop decides, with the options of "Review-loop configuration".

Collect the open decisions of all N plans, and each finding that a plan-review fixer did not resolve with confidence. If the list is empty, start Step 3 without a stop. Else, outside the full mode, ask the user all of them in one batch before Step 3. In the full mode, decide each one as "Autonomy" says, write the decision into its plan, and start Step 3. Do not carry ambiguity into the implementation. The plan-review loops run without the routine triage stop. "Review-loop configuration" says which findings still reach the user.

**Step 2 makes no commit.** The planners and the plan-review loops change only the plan files. The plan files stay out of commits (see "Guardrails"). So each plan-review loop runs `dev-essentials:review-loop` with `--no-commit`, which turns off its Phase 7. The next cycle of that loop reviews the plan file again, as the fix pass changed it.

### Step 3 — Per-task cycle (repeat for each of the N tasks, sequentially)

For task `i`:

1. **Record the base SHA of the task**: `TASK_BASE_SHA[i] = git -C "<worktree>" rev-parse HEAD`.
2. **Implement.** Dispatch an implementer subagent with the absolute worktree path, the plan file, and the guard "implement only this task". With `--no-worktree`, also give it the files of the user from Step 1, which it must not write. The brief tells it not to commit, because the session makes the commit in item 4. Name the skills for the change type (domain models, tests, controllers, configuration, and others), and the build and test commands that prove the work done. It marks the plan items `- [ ]` → `- [x]` as they complete.
3. **Build and test** before the commit. The implementer runs its own build and tests, and reports the verbatim result lines. Then run the build and test commands of the plan one time in the worktree, as item 1 of the section `Trust but verify` in `dev-essentials:subagent-orchestration` says. If the result differs from the report, or the run is red, resume the implementer with the error lines, and run again. Never give a red signal to the review loop. Own every failure of this session (`dev-essentials:engineering-discipline` Rule 1). For .NET, follow `dev-essentials:dotnet-build-test`.
4. **Commit** the implementation of the task. Stage explicit paths, never `git add -A` or `git add .`: only the source and test changes of this task. Never stage a plan file (see "Guardrails"). Record the SHA of the commit in `TASK_COMMITS[i]`.
5. **Review-loop the implementation** with `dev-essentials:review-loop` and `target=diff <TASK_BASE_SHA[i]>..HEAD`. Keep its commit for each review cycle. Add the SHA of each commit that the loop makes to `TASK_COMMITS[i]`.
6. **Squash the commits of this task into one**, from `TASK_BASE_SHA[i]` to `HEAD`, with the script `squash_task.py` of this plugin. It needs Python 3 and git. On Windows, run it in the Bash tool (Git Bash). Give one `--commit` for each SHA of `TASK_COMMITS[i]`, and the plan folder as `--plan-dir`:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/squash_task.py" --repo "<worktree>" --plan-dir "<plan folder>" --base <TASK_BASE_SHA[i]> --commit <sha> --commit <sha> --message "<Issue ref> — <summary> (implement + <rounds> review rounds)" --apply
   ```

   - Take the SHAs from the commits that this run made, never from `git log` of the range. A list from the log hides the commit of someone else.
   - The script makes each check before the squash. It refuses a commit of the range that is not a `--commit`, and a merge commit. It also refuses a changed tracked file, a staged plan file, a detached HEAD, and a plan file in the commits. A refusal changes nothing.
   - `RESULT: REFUSED` (exit code 3) is the squash-base safety stop. **Stop and ask the user**, and show the `REFUSED`, `COMMIT`, `MISSING`, `CHANGED`, and `PLAN FILE` lines. Never squash across the commit of someone else. In the full mode, do not stop. Skip this squash, keep the commits as they are, and report the refusal.
   - `RESULT: ONE COMMIT`: the review loop made no commit, so the task already has one commit. The script makes no commit. Say so.
   - `RESULT: SQUASHED`: the `NEW` line gives the SHA of the task commit. Report each `WARN` line.
   - `RESULT: FAILED` (exit code 1), for example after a failed commit hook: the script put the old HEAD back. Show the `FAILED` and `OUTPUT` lines to the user, and ask. If the `RESULT` line says `NOT RESTORED`, first run `git -C "<worktree>" reset --soft <OLD HEAD>`. After a `RESTORED` line, this command changes nothing.
   - An `OLD HEAD` line and no `RESULT` line: an error, for example Ctrl+C, stopped the script after it moved the branch. This output has no `OUTPUT` line, so show the last line of the error output to the user, and ask. After a `RESTORED HEAD` line, the old HEAD is back and nothing needs an undo. With no `RESTORED HEAD` line, the restore failed: show the output to the user, and give the command `git -C "<worktree>" reset --soft <OLD HEAD>`.
   - If `python3` is not available, or the script exits with code 2, keep the commits as they are, and ask the user. If the output has no `RESULT` line and no `OLD HEAD` line, do the same. In the full mode, report the problem instead.
7. Report one status line, and go to task `i+1`.

### Step 4 — Final cross-task review

1. Record `FINAL_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.
2. Run `dev-essentials:review-loop` once over the **combined** work, with `target=diff <BATCH_BASE_SHA>..HEAD`. This pass finds what single-task reviews cannot: inconsistency across tasks, duplicated abstractions, contradictory assumptions, and coverage gaps at the seams.
3. Commit once for each review cycle, as the loop does by default. Record the SHA of each commit that the loop makes.
4. **Squash only the commits of this pass**, from `FINAL_BASE_SHA` to `HEAD`, with the script of Step 3.6: the same `--repo` and `--plan-dir`, `--base <FINAL_BASE_SHA>`, one `--commit` for each commit of the final loop, and `--message "Final review across <N> tasks — <summary of fixes>"`. The N task commits of Step 3 stay as they are. The rules of Step 3.6 for each output of the script apply, also the squash-base safety stop. If the final loop made no commit, there is nothing to squash, so do not run the script. Report N commits and no final-review commit. Do not invent one.

### Step 5 — Report

- Push nothing in this step. Step 6 holds the push, the pull request, and the merge.
- Report the real commit topology: `git -C "<worktree>" log --oneline <BATCH_BASE_SHA>..HEAD`. The expected end state is **N task commits plus at most 1 final-review commit**. If the real topology differs, report it and explain why. Never report the planned shape as a fact.
- For each task: what was implemented, which files, the review-loop verdict (`stop-clean`, `stop-max-rounds`, or `stop-blocked`), and the subject of the squashed commit.
- The paths of the N plan files. They are not in any commit.
- For the batch: the verdict of the final review, the build and test state at `HEAD`, and each decision that needed a sign-off with its outcome. Also each gate that this run passed without a stop, and each finding deferred by agreement. In the full mode, also list each decision that the run made for the user under "Decisions for your review".
- The absolute worktree path, the branch name, and the head commit at the end of the run.

### Step 6 — Finish (push, pull request, merge)

Read `${CLAUDE_PLUGIN_ROOT}/skills/work-modes/references/finish.md`, and do its steps in the worktree. With `--no-worktree`, the worktree is the folder of the user, so remove no worktree in item 3 of Step 4 of `dev-essentials:merge-pr`. If the run has `--no-worktree` and a linked worktree holds the branch, also keep the branch. Name both in the finish report. The base branch is the Step 0 base. The review verdicts are the verdicts of the Step 3 loops and of the Step 4 loop. In the partial mode and in the interactive mode, ask the question of its final gate after the Step 5 report.

## Review-loop configuration

Every review loop of this skill (Step 2, Step 3, and Step 4) invokes `dev-essentials:review-loop` and reimplements none of its mechanics. This skill wants the "Default configuration" of that skill. It overrides only one point: the Step 2 loops pass `--no-commit` (see the last item). Only these options belong to this skill:

- `--rounds=<N>` from the `--rounds` of this skill (default `2`), passed to every loop.
- **The interactive mode**: outside it, every loop runs without the Phase 4 triage stop. In it, pass `--mode interactive` to the Step 3 loops and to the Step 4 loop. Pass `--mode partial` to the Step 2 plan-review loops.
- **The full mode**: pass `--mode full` to every loop, also to the Step 2 plan-review loops. Outside it, a plan-review loop still asks the user at its own Phase 4 about a finding that is not clear-cut. A finding that a plan-review fixer did not resolve with confidence waits for the Step 2 batch.
- Commit after each review cycle in the Step 3 and Step 4 loops, so that the squashes are well defined. The Step 2 loops pass `--no-commit` and commit nothing, because a plan file stays out of commits.
