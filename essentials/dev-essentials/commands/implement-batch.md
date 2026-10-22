---
description: Implement N related tasks in one branch or worktree. Plan and review each task, then make one squashed commit per task and one final review across all tasks. Pushes only with --push.
argument-hint: <parent issue reference, or an explicit list of N tasks> [--base=<branch>] [--worktree=<branch-ref>] [--plan-dir=<path>] [--rounds=N] [--push] [--interactive] [--autonomous]
---

# Implement Batch (N tasks, N commits + at most 1 final-review commit)

## Division of labor in this command family

- `dev-essentials:implement` runs the tasks of an existing plan file, with no research and no review loop.
- `dev-essentials:opsx-implement` implements phases of an existing OpenSpec change, with no research and no review.
- `dev-essentials:research-implement-review-report` (RIRR) works one task: research, a plan, the implementation, a review loop, and a report.
- `dev-essentials:implement-task` wraps RIRR for one task. It adds a sweep of extra context first and a `/simplify` commit at the end.
- `dev-essentials:implement-batch` works N related tasks in one branch: one squashed commit for each task, then one final review across the tasks.
- `dev-essentials:feature-pipeline` runs a tracked task from the task provider (for example, GitHub Issues or Jira) end-to-end in an isolated git worktree. It has one subagent for each stage and its own approval gates.

**Arguments**: $ARGUMENTS

- Format: `<parent issue reference, or an explicit list of N tasks> [options]`
- Examples (no value in them is fixed behavior):
  - `Issue 1469733 — implement all its sub-issues --base=release/2.0 --worktree=vvasilyev/tasks/1469733-custom-retention-enhancements`
  - `Notes/Plans/custom-retention-plan.md — implement every task in this plan --base=release/2.0`
  - `1) add the retention option 2) wire it through the scheduler 3) cover it with tests --base=release/1.0 --worktree=vvasilyev/tasks/987654-retention`
- **N comes from the input of the user**: the list, the plan file, or the sub-issues of the parent. Never assume a count, and never drop or add a task silently.
- If $ARGUMENTS is empty, use the **AskUserQuestion** tool to ask which tasks to implement.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`, `master`, or `develop`. |
| `--worktree=<branch-ref>` | ask or derive | The branch ref that all N tasks share. Use the ref that this flag or the prose of $ARGUMENTS names, verbatim. Else build `<prefix>/<parent-type>s/<parent-ID>-<slug>` from the branch-naming convention in the `CLAUDE.md` of the repo or of the user. Without a convention, **ask once**. |
| `--plan-dir=<path>` | `Notes/Plans/` | The folder inside the worktree for the plan files. A plan location that the repo documents wins. |
| `--rounds=<N>` | `2` | Review-loop cycles, passed as `--rounds` to every loop: the plan loops, the code loops, and the final loop. |
| `--push` | off | Push the finished stack after the final report. **Off unless the user asks for it in this invocation.** |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

## Autonomy

This workflow has three modes. The user picks one with a flag.

- Default (no flag): the run does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. The dangerous gates still stop. A dangerous gate comes before deletion of data, a post to an outside system, a push, or pull request creation. Examples of posts: GitHub comments, reviews, and issues, or documentation pages.
- `--interactive`: every gate stops and waits for the user, as the gate text says.
- `--autonomous`: no gate stops. This includes the dangerous gates. The flag is the yes of the user at each gate of this workflow, also at a gate whose text asks for an explicit yes. The run still stops for a question that blocks the work (see below).

These rules apply in all modes:

- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run passed without a stop. With `--autonomous`, also list each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It does not add steps. Some steps run only with a flag such as `--push`, `--commit-push`, or `--apply`, or only on a request of the user. Such a step still needs that flag or request.
- A flag that names an action approves that action for this run, so the action needs no new stop. Examples: `--push` and `--commit-push`. An action that a step of this workflow names as its default needs no new stop either.
- If this workflow has a merge step and the branch policy allows a merge without a review, `--autonomous` merges. Else it does not merge. Never bypass branch protection. Do not use an admin override, a force push, or a change to the branch policy. In the other modes, the merge stays with the user.
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If both checks below pass, you can delete such a branch with `git branch -D`. First, its pull request is merged. Find the pull request with `list_pull_requests`, with `head: "<owner>:<branch>"` and `state: "all"`. `<owner>` is the `owner` value of the call. The default state lists open pull requests only, and GitHub ignores a `head` value without the `<owner>:` prefix. Then read the pull request with `pull_request_read` (`method: "get"`), and make sure that `merged` is `true`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the run cannot read the state of the pull request, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on. Exception: do not pass `--interactive` to the Step 2 plan-review loops (see "Review-loop configuration").

## Subagent dispatch

Read `dev-essentials:subagent-orchestration` before the first dispatch. Its rules apply to every dispatch. A bare "Rule N" in this file is one of them. This command adds these:

- **Delegate almost everything.** The orchestrating session only resolves the arguments, dispatches, does the git bookkeeping (commits, squashes, SHA records), and talks to the user. It does not read source files, write code, or review diffs. Each brief asks for a short structured report (verdicts, `file:line` anchors, commands and results), never pasted diffs or file dumps.
- **Models**: Opus plans and reviews, and Sonnet implements and fixes. A task that the plan gives as an explicit 1-2-3 edit list uses Haiku. The build and test check of the orchestrating session uses Haiku, through the agent type `dev-essentials:test-runner`. A code search uses Haiku, through `dev-essentials:code-locator`. These agent types set their own model, so their dispatches pass no `model`. This line is the one home of these models, and the steps below name only the role. Haiku can do a mechanical extraction, such as the list of sub-issues. All follow "Model selection" in `dev-essentials:subagent-orchestration`.
- **Effort**: pass `effort` on each dispatch of a general agent type. The planner of Step 2: `high`, or `xhigh` for a large plan or a change on the critical path. The implementer of Step 3: `high`. For a task that the plan gives with its exact files and edits, use `medium`. An edit-list implementer and a mechanical extraction: `low`. `dev-essentials:review-loop` sets the effort of the reviewer and the fixer. The agent types of the "Models" line set their effort in their agent files, so their dispatches pass no `effort`. This line is the one home of these effort levels. It agrees with the "Effort" line of `dev-essentials:research-implement-review-report`.
- **Parallel where safe, sequential where not.** All N tasks share one worktree. Two dispatches can run at the same time only under two rules. Each one writes its own path. Neither one runs a git command that changes the worktree, the index, or the history. Such commands are `add`, `commit`, `checkout`, `reset`, and branch operations, but not `log`, `show`, or `diff`.
  - The Step 2 planners qualify. Each one writes only its own `<--plan-dir>/<task-slug>-plan.md`, and uses git only to read (for example for `file:line` anchors). Dispatch them in parallel, and write both rules into every planner brief.
  - The implementation does not qualify. The Step 3 implementers edit shared product and test files, and they commit. So implement and review **strictly one task at a time**. The same holds for the Step 2 plan-review loops (they commit) and the Step 4 final loop.
- Fable is for exceptional cases only. Never dispatch it silently on your own initiative. With `--interactive`, ask the user before each Fable dispatch, also where the model matrix allows Fable. Without `--interactive`, follow "Autonomy".
- A bounded dispatch does the work itself, and does not delegate it again (Rule 7). Examples: the plan of one task, one implementation, or one fix.

## Guardrails

- **One task per commit** in the final stack. Do not merge two tasks into one commit or split one task across two, unless the user asks. One exception: the commit of task 1 also holds the Step 2 plans commit (Step 3.1). The guard "implement only this task" of Step 3.2 still binds the implementer of task 1. Only the squash of the orchestrating session takes in the plans commit.
- **Own every red signal** from each build or test run in this session (`dev-essentials:engineering-discipline` Rule 1). Never call one "pre-existing", and do not search the history to find out whether it predates the batch.
- **Do not improvise.** Ask the user about an unclear plan item, an ambiguous review finding, or a task that is bigger than its plan. Do not guess. With `--autonomous`, decide as "Autonomy" says.
- The plan files are the source of truth. Keep them up to date as tasks complete.

## Progress tracking for the user

Keep a task list with one entry for each task and one for the final review, and update it. Use `TodoWrite`, or `TaskCreate`, `TaskUpdate`, and `TaskList`, whichever this session has. The list is for the user only, never for coordination between subagents.

## Steps

### Step 0 — Resolve the batch

1. Find the task list, and so **N**:
   - An explicit list in $ARGUMENTS: use it verbatim, in the given order.
   - A plan file path: use the task or phase list of the plan.
   - A parent issue reference: dispatch a subagent that lists its sub-issues from the tracker (Rule 4, and `dev-essentials:github-mcp-conventions` for GitHub). State the list and its count in one status line, and repeat them in the final report. Without `--interactive`, start the work. With `--interactive`, **show the list to the user for approval** before the work starts. An explicit list needs no approval.
2. Resolve `--base` and `--worktree` as the Options table says.
3. If a material fact is missing or unclear, ask with the **AskUserQuestion** tool before any work. Examples: which tasks, which branch, the worktree name, or the intended order and dependencies. If nothing is unclear, start the work.
4. Fix the **order** of implementation: the order of the user, else the dependency order of the plan. State the order in one line.

### Step 1 — Worktree setup

Create the worktree from the Step 0 base branch with `dev-essentials:git-worktree-management`, and run its post-create bootstrap. Record the absolute worktree path. Each write-capable dispatch from here on carries it (Rule 6), and each git call uses `git -C "<abs worktree path>"`.

Then record `BATCH_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.

### Step 2 — Plan every task

Dispatch planners in parallel, one for each task. Each one writes `<--plan-dir>/<task-slug>-plan.md` inside the worktree. A plan holds the scope of the task, the files that it touches, and the patterns that it must follow (with `file:line` anchors). It also holds its verification commands and each open decision. An open decision is a critical decision that the task, the code, and the documentation do not settle (`dev-essentials:engineering-discipline` Rule 2).

Then, for each plan, run `dev-essentials:review-loop` with `target=spec <plan path>`, and fix the plan as the loop decides, with the options of "Review-loop configuration".

Collect the open decisions of all N plans, and each finding that a plan-review fixer did not resolve with confidence. If the list is empty, start Step 3 without a stop. Else, without `--autonomous`, ask the user all of them in one batch before Step 3. With `--autonomous`, decide each one as "Autonomy" says, write the decision into its plan, and start Step 3. Do not carry ambiguity into the implementation. The plan-review loops run without the routine triage stop. "Review-loop configuration" says which findings still reach the user.

**Step 2 makes exactly one commit, before Step 3 starts.** The planners commit nothing. When the planners return, and before the first plan-review loop, stage the N plan files by explicit path, and commit them: `git -C "<worktree>" commit -m "Plans for <N> tasks"`. The N plan-review loops run one at a time and commit per cycle. When every plan is reviewed and every open question is answered or decided, stage the N plan files again by explicit path. A decision can change a plan after the loops. Then squash all Step 2 commits into one:

```bash
git -C "<worktree>" reset --soft <BATCH_BASE_SHA>
git -C "<worktree>" commit -m "Plans for <N> tasks (<N> plan reviews)"
```

The squash-base safety stop of Step 3.6 applies. The squash of task 1 takes in this one commit (Step 3.1).

### Step 3 — Per-task cycle (repeat for each of the N tasks, sequentially)

For task `i`:

1. **Record the base SHA of the task.** For task 1, `TASK_BASE_SHA[1] = BATCH_BASE_SHA` from Step 1, **not** a new `rev-parse`. So the Step 3.6 squash of task 1 also takes in the plans commit. For tasks 2 to N, `TASK_BASE_SHA[i] = git -C "<worktree>" rev-parse HEAD`. Also record `REVIEW_BASE_SHA[i] = git -C "<worktree>" rev-parse HEAD`. For task 1, this is the Step 2 plans commit, so the review of task 1 does not see the plans.
2. **Implement.** Dispatch an implementer subagent with the absolute worktree path, the plan file, and the guard "implement only this task". Name the skills for the change type (domain models, tests, controllers, configuration, and others), and the build and test commands that prove the work done. It marks the plan items `- [ ]` → `- [x]` as they complete.
3. **Build and test** before the commit. The implementer runs its own build and tests. Then dispatch `dev-essentials:test-runner` with the absolute worktree path and the build and test commands of the plan. Compare its verbatim result lines with the report of the implementer. If they differ, or the status is not GREEN, resume the implementer with the report of the test runner. Never give a red signal to the review loop. Own every failure of this session (`dev-essentials:engineering-discipline` Rule 1). For .NET, follow `dev-essentials:dotnet-build-test`.
4. **Commit** the implementation of the task. Stage explicit paths, never `git add -A` or `git add .`: the source and test changes of this task, and only the plan file of this task (`<plan-dir>/<this-task-slug>-plan.md`). Never stage the plan file of another task, also a dirty one.
5. **Review-loop the implementation** with `dev-essentials:review-loop` and `target=diff <REVIEW_BASE_SHA[i]>..HEAD`. Keep its commit for each review cycle.
6. **Squash the commits of this task into one**, from `TASK_BASE_SHA[i]` to `HEAD`:

   ```bash
   git -C "<worktree>" reset --soft <TASK_BASE_SHA[i]>
   git -C "<worktree>" commit -m "<Issue ref> — <summary> (implement + <rounds> review rounds)"
   ```

   If a commit in this range is not work of this task, **STOP and ask the user** before the soft reset (the squash-base safety stop). Never squash across the commit of someone else. With `--autonomous`, do not stop. Skip this squash, keep the commits as they are, and report the unexpected commit. For task 1, the Step 2 plans commit in this range is expected and does not trigger the stop. If the review loop made no commit, the task already has one commit, and the squash does nothing. Say so, and make no empty commit.
7. Report one status line, and go to task `i+1`.

### Step 4 — Final cross-task review

1. Record `FINAL_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.
2. Run `dev-essentials:review-loop` once over the **combined** work, with `target=diff <BATCH_BASE_SHA>..HEAD`. This pass finds what single-task reviews cannot: inconsistency across tasks, duplicated abstractions, contradictory assumptions, and coverage gaps at the seams.
3. Commit once for each review cycle, as the loop does by default.
4. **Squash only the commits of this pass**, from `FINAL_BASE_SHA` to `HEAD`:

   ```bash
   git -C "<worktree>" reset --soft <FINAL_BASE_SHA>
   git -C "<worktree>" commit -m "Final review across <N> tasks — <summary of fixes>"
   ```

   The N task commits of Step 3 stay as they are. The same squash-base safety stop applies. If the final loop made no commit, there is nothing to squash. Report N commits and no final-review commit. Do not invent one.

### Step 5 — Report and stop

- **Do not push.** Report and wait for the review of the user. Push only with `--push` in this invocation, and only after you deliver the report.
- Report the real commit topology: `git -C "<worktree>" log --oneline <BATCH_BASE_SHA>..HEAD`. The expected end state is **N task commits plus at most 1 final-review commit**. If the real topology differs, report it and explain why. Never report the planned shape as a fact.
- For each task: what was implemented, which files, the review-loop verdict (`stop-clean`, `stop-max-rounds`, or `stop-blocked`), and the subject of the squashed commit. For task 1, say that its commit also holds the Step 2 plan-review fixes of all tasks.
- For the batch: the verdict of the final review, the build and test state at `HEAD`, and each decision that needed a sign-off with its outcome. Also each gate that this run passed without a stop, and each finding deferred by agreement. With `--autonomous`, also list each decision that the run made for the user under "Decisions for your review".
- The absolute worktree path and the branch name.

## Review-loop configuration

Every review loop of this command (Step 2, Step 3, and Step 4) invokes `dev-essentials:review-loop` and reimplements none of its mechanics. This command wants the "Default configuration" of that skill, so it overrides nothing. Only these options belong to this command:

- `--rounds=<N>` from the `--rounds` of this command (default `2`), passed to every loop.
- **`--interactive`**: without it, every loop runs without the Phase 4 triage stop. With it, pass `--interactive` to the Step 3 loops and to the Step 4 loop. Do not pass it to the Step 2 plan-review loops.
- **`--autonomous`**: pass it to every loop, also to the Step 2 plan-review loops. Without it, a plan-review loop still asks the user at its own Phase 4 about a finding that is not clear-cut. A finding that a plan-review fixer did not resolve with confidence waits for the Step 2 batch.
- Commit after each review cycle in every loop, so that the squashes are well defined.
