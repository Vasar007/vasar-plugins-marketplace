---
description: Research, plan, implement, review-loop, and report for one task, end-to-end in one session. Needs no spec change (unlike opsx-implement), and does not stop before the review (unlike implement).
argument-hint: <task description, plan file path, or issue reference> [--base=<branch>] [--branch-prefix=<prefix>] [--commit-mode=per-phase|single] [--rounds=N] [--context=<path>...] [--skip-research] [--interactive] [--autonomous]
---

# Research → Implement → Review-Loop → Report

## Division of labor in this command family

- `dev-essentials:implement` runs the tasks of an existing plan file, with no research and no review loop.
- `dev-essentials:opsx-implement` implements phases of an existing OpenSpec change, with no research and no review.
- `dev-essentials:research-implement-review-report` (RIRR) works one task: research, a plan, the implementation, a review loop, and a report.
- `dev-essentials:implement-task` wraps RIRR for one task. It adds a sweep of extra context first and a `/simplify` commit at the end.
- `dev-essentials:implement-batch` works N related tasks in one branch: one squashed commit for each task, then one final review across the tasks.
- `dev-essentials:feature-pipeline` runs a tracked task from the task provider (for example, GitHub Issues or Jira) end-to-end in an isolated git worktree. It has one subagent for each stage and its own approval gates.

**Arguments**: $ARGUMENTS

- Format: `<task description, plan file path, or issue reference> [options]`
- Examples:
  - `Issue 123456 — wire the overwrite-existing-records flag through to the import pipeline`
  - `Notes/Plans/my-existing-plan.md` goes straight to Phase 2 with this plan. Phase 1 still runs briefly to load earlier context.
  - `Fix the SingleOrDefault() 500 in InvoiceValidator --rounds=3`
  - `Create a worktree vvasilyev/tasks/123456-overwrite-existing-records from release/2.0, then follow this command's workflow.` names the branch and the base branch, so Phase 0 does not derive a branch name.
- If $ARGUMENTS is empty, use the **AskUserQuestion** tool to ask what to work on.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`, `master`, or `develop`. |
| `--branch-prefix=<prefix>` | derive from context, else ask | The prefix of the task-branch name of Phase 0. If a `CLAUDE.md` of the project or of the user states a branch-naming convention, take the prefix from it. Else ask the user once per run, before you create the branch. |
| `--commit-mode=<per-phase\|single>` | `per-phase` | `per-phase`: one commit after Phase 2 (Implement), then the commits of each Phase 3 round. `single`: run every phase and every review round the same way, but squash the whole run into **one commit at the end** (see "Commit cadence"). |
| `--rounds=<N>` | `2` | Review-loop cycles. Passed to `dev-essentials:review-loop` as `--rounds`. |
| `--context=<path>` | auto | A research or handoff file to load, instead of fresh research or in addition to it. The resolution is the same as for the `--context` of `dev-essentials:implement`. **Repeatable**: the run reads every path, and no path replaces another. |
| `--skip-research` | off | Skip Phase 1, for example to resume a session whose plan exists and is current. Phase 2 still loads each `--context`. |
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
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Subagent dispatch

Read `dev-essentials:subagent-orchestration` before the first dispatch. Its rules apply to every dispatch, and this command adds these:

- **Models**: research and planning (Phase 1) and review (Phase 3) use Opus. Implementation and fixes (Phase 2, and the fixer of Phase 3) use Sonnet. All follow "Model selection" in `dev-essentials:subagent-orchestration`.
- Fable is for exceptional cases only. Never dispatch it silently on your own initiative. With `--interactive`, ask the user before each Fable dispatch, also where the model matrix allows Fable. Without `--interactive`, follow "Autonomy".

## Guardrails

- **Do not improvise**. If the right resolution of a research finding, a plan ambiguity, or a review finding is unclear, ask the user. Do not guess. With `--autonomous`, decide as "Autonomy" says.
- **Own every red signal** from the build and test steps of Phase 2 and Phase 3 in this session (`dev-essentials:engineering-discipline` Rule 1). Never call one "pre-existing", and do not search the history to find out whether it predates this run.
- **Never push without the explicit go-ahead of the user, each time.**

## Progress tracking for the user

Keep a task list with one entry for each phase (Research & Plan, Implement, Review loop, Report), and update it. After Phase 2 knows the tasks, add one entry for each task. Use `TodoWrite`, or `TaskCreate`, `TaskUpdate`, and `TaskList`, whichever this session has. Without such a tool, use the boxes of the plan file and a short status line at the top of each reply. The list is for the user only, never for coordination between subagents. The plan file stays the source of truth.

## Phases

### Phase 0 — Branch & worktree setup

0. **A worktree and branch that already exist: verification only.** Case: the caller says that the worktree and the branch exist, and gives the branch name and the absolute worktree path. A wrapper such as `dev-essentials:implement-task` does exactly this. In this case, Phase 0 is only a verification step: find out whether `git -C "<worktree path>" rev-parse --abbrev-ref HEAD` prints the expected branch.
   - If it does, skip steps 1 to 3, and run every later phase in that worktree. Do **not** derive a branch name again, and do **not** create a second worktree or branch.
   - If it does not, STOP and ask the caller or the user. Do not create a branch or a worktree to recover.
   - If the caller gave no worktree or branch, go on with step 1.
1. Resolve the **base branch** as the `--base` row of the Options table says.
2. Resolve the **task branch name**. If $ARGUMENTS names a branch (as in the worktree example of "Arguments"), use it verbatim. Else resolve `--branch-prefix` first (see the Options table). Then build the name from that prefix and the issue reference in $ARGUMENTS, by the type or label of the GitHub issue:

   | Source | Branch name pattern | Example (`--branch-prefix=vvasilyev`) |
   | --- | --- | --- |
   | GitHub issue typed/labeled `task` | `<branch-prefix>/tasks/<ID>-<short-description>` | `vvasilyev/tasks/123456-add-invoice-pagination` |
   | GitHub issue typed/labeled `bug` | `<branch-prefix>/bugs/<ID>-<short-description>` | `vvasilyev/bugs/123456-fix-timeout` |
   | GitHub issue, any other type/label `<type>` | `<branch-prefix>/<type>s/<ID>-<short-description>` | `vvasilyev/features/123456-add-x` |
   | Research (no issue at all) | `<branch-prefix>/researches/<short-description>` | `vvasilyev/researches/investigate-y` |

   `<ID>` is the issue number from $ARGUMENTS. For example, `Issue 123456` or `#123456` gives `123456`. The research pattern has no `<ID>` part. `<short-description>` is a short kebab-case slug of the task description. If the type or label of the issue is unknown and the task is not research, do this. Without `--interactive`, use the `tasks` pattern, and say so in the final report. With `--interactive`, ask the user which pattern applies, and do not guess.
3. If $ARGUMENTS asks for a worktree (for example "Create a worktree ... from ..."), create it with `dev-essentials:git-worktree-management`, from the base branch of step 1 and with the branch name of step 2. Else create the branch, or check it out, as `dev-essentials:git-sync` says.
4. Run every later phase in that branch or worktree.

### Phase 1 — Research & Plan

With `--skip-research`, skip this phase.

1. Resolve each `--context=<path>` (the flag is repeatable). Without one, derive a context file as `dev-essentials:implement` does: from a plan-file argument, or from the auto-memory folder as a last fallback. Read all of them in the orchestrating session before any dispatch. Pass their findings verbatim into every research brief.
2. Dispatch one or more **Opus** research subagents. They work from the real code, not from assumptions. They find out what already exists, which files are involved, which patterns the code around it uses, and what is unclear or open. Pass the scope and context of the user verbatim into each brief. If the task splits in a natural way, dispatch several research subagents at the same time. For example: one on the production code path, one on the test coverage, and one on a permission or contract question.
3. Dispatch an **Opus** planning subagent (the same dispatch as step 2, or a later one). It turns the research into a concrete plan: ordered tasks or phases, the exact files of each, and the open decisions. An open decision is a critical decision that the task, the code, and the documentation do not settle. Examples: an ambiguous change of behavior, or a change of a public contract. Also anything that the current spec or plan does not cover (`dev-essentials:engineering-discipline` Rule 2).
4. Save the plan to `Notes/Plans/<slug>-plan.md`, or to the location that the `CLAUDE.md` of the repo documents. This is the plan sign-off gate:
   - Without `--interactive`, report the plan path in one status line, and start Phase 2.
   - With `--interactive`, **show the plan to the user for sign-off before Phase 2 starts**. Resolve here each open question that the user raises.
   - If the plan lists open decisions, handle them before Phase 2. Without `--autonomous`, ask them all in one message, and start Phase 2 after the answers. With `--autonomous`, decide them as "Autonomy" says, write each decision into the plan, and start Phase 2.

   Do not carry ambiguity into Phase 2.

### Phase 2 — Implement

1. Load the plan from Phase 1, the plan file of the argument, or `--context` for a resumed session. Both shapes of `--context` must work here, not only be accepted:
   - **Plan-shaped** (it has a task checklist): use it as it is.
   - **A research or handoff file without a checklist**: derive a task list from its content. Do not refuse the file.
   - **Several `--context` paths**: a plan-shaped file gives the task list, and the others are research context. Without a plan-shaped file, derive the task list from all of them.
2. For each task or phase of the plan, dispatch a **Sonnet** subagent with the brief rules of `dev-essentials:implement` Step 4. Follow the existing patterns, ask and do not improvise, and use the skills that fit the change type (domain models, tests, controllers, configuration, and others).
3. Mark each task done in the plan file as it completes (`- [ ]` → `- [x]`).
4. Build and test after each task. For small and tightly coupled tasks, you can build and test once after all of them. Never leave a red signal for the review loop.
5. For the commits of this phase, see "Commit cadence".

### Phase 3 — Review loop

Invoke `dev-essentials:review-loop` on the output of Phase 2: `target=branch` in the common case, or `target=diff <range>` to review only part of the work. Do not reimplement its mechanics. Its section "Default configuration" is what this command wants, so override nothing. Pass only these options of this command:

- `--rounds=<N>` from the `--rounds` of this command (default `2`).
- `--interactive` or `--autonomous`, for a run that has it.

Record each finding that the user and the orchestrating session agree to defer, as deferred in the Phase 4 report. "Commit cadence" says how the commits of each loop round fit the commit mode.

### Phase 4 — Report

Write the handoff document with `dev-essentials:save-context`, and follow all of its steps. Pass the path `Notes/Results/<slug>-report.md` as its path argument. Pass no flag. This also applies to `--plan` and to the mode flag of this run. It is an exception to the last rule of "Autonomy". `save-context` finds the plan of Phase 1 in the conversation (its Step 1). So `save-context` runs in its default mode, also in a run with `--autonomous`. It runs its Step 5 cleanup and prints no continuation prompt. Before it deletes a file of an older session, its Step 5 asks the user. If another command follows the steps of `save-context`, the cleanup runs only when that command asks for it. This phase is the last step of the run, so ask for the cleanup. Also tell the cleanup to keep every file of this run, except a `_`-prefixed progress file whose task is done. These are the plan, the review reports, the report, and each context document of a wrapper such as `implement-task`. The branch of this run is not merged, and the user still reviews it. If the repo documents its own path, use that. For a run that continues a numbered session sequence of the user, use a `-handoff-N.md` name. The report has these sections:

- **Overview**: what this run covered, the branch, the worktree, and the date.
- **What Was Done**: for each phase, the research findings, the plan, each implemented task, and the outcome of each review round.
- **Key Decisions**: a table with the reasons. It holds each decision that Phase 1 or Phase 3 asked the user to sign off. It also holds each gate that this run passed without a stop. With `--autonomous`, also list each decision that the run made for the user under "Decisions for your review".
- **Issues Found**: what this run found but did not cover, candidate follow-up issues, and each process problem to report to the user.
- **Key File Paths**: grouped by category (core, tests, configuration, docs).
- **What's Next**: the remaining work. Say whether the branch is pushed or has a PR. The default is no, because a push needs the explicit go-ahead of the user.

Tell the user where the report is. Give the same one-line summary as `save-context`, and say what its Step 5 cleanup did. Also give the final verdict of the review loop (`stop-clean`, `stop-max-rounds`, or `stop-blocked`). Print the report only. Step 5 can list files or branches that wait for the yes of the user. If it does, ask its one Step 6 question after the report. When the user says yes, delete the listed files in this session, with the safety rules of Step 5. If the user asks for a continuation prompt in this run, print it last. Else print no continuation prompt for the next session.

## Commit cadence

### Per-phase mode (default)

- **After Phase 2 completes** (all tasks of this run implemented, built, and tested green), make one commit. If the plan has several independent tasks, one commit for each task is also fine. Follow the structure of the plan. Never go into Phase 3 with uncommitted Phase 2 output.
- **During Phase 3**, the review loop commits once per round by default. Do not suppress this.

### Single-commit mode (`--commit-mode=single`)

- Before Phase 2 starts, record the SHA of `HEAD`.
- Run Phase 2 and Phase 3 as described above, with the normal round commits of the review loop. Do not suppress them with `--dry-run` or `--no-verify-fix`. Both flags also skip the fix itself.
- After Phase 3, and **before** the Phase 4 report, squash the whole run into one commit: `git reset --soft <recorded-SHA>`, then one commit. Its message sums up the implementation and the fixes of each review round, for example `Task X — <summary> (implement + N review rounds)`.
- **The squash-base safety stop**. If a commit from outside this run landed on `HEAD` (for example an unrelated concurrent commit), **stop and ask the user** before the soft reset. Do not squash across the commit of someone else. With `--autonomous`, do not stop. Skip the squash, keep the commits as they are, and report the unexpected commit.
- A caller can run this mode on a branch where others can also commit, for example a shared PR branch. That caller must make sure that nothing else commits between the recorded SHA and the squash. This command does not coordinate it for the caller.
