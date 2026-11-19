---
name: research-implement-review-report
description: Research, plan, implement, review-loop, and report for one task, end-to-end in one session. Needs no spec change (unlike opsx-implement), and does not stop before the review (unlike implement).
argument-hint: <task description, plan file path, or issue reference> [--base=<branch>] [--branch-prefix=<prefix>] [--commit-mode=per-phase|single] [--rounds=N] [--context=<path>...] [--skip-research] [--mode interactive|partial|full]
---

# Research → Implement → Review-Loop → Report

## Division of labor in this skill family

- `dev-essentials:implement` runs the tasks of an existing plan file, with no research and no review loop.
- `dev-essentials:opsx-implement` implements phases of an existing OpenSpec change, with no research and no review.
- `dev-essentials:research-implement-review-report` (RIRR) works one task: research, a plan, the implementation, a review loop, and a report.
- `dev-essentials:implement-task` wraps RIRR for one task. It adds a sweep of extra context first and a `/simplify` commit at the end.
- `dev-essentials:implement-batch` works N related tasks in one branch: one squashed commit for each task, then one final review across the tasks.
- `dev-essentials:feature-pipeline` runs one task end-to-end in an isolated git worktree. The task is a tracked task of the task provider (for example, GitHub Issues or Jira), or a plain request. Subagents run its stages from the requirements to the reviews, the session pushes and opens the PR, and it has its own approval gates.

The configured branch prefix is `${user_config.branch_prefix}`. The notes folder is `${user_config.notes_dir}`. Set both with `/plugin configure` (see `plugin.json`). If a value still shows as a `${...}` placeholder, no value is saved. Then the configured branch prefix is empty, and the notes folder is `Notes`.

**Arguments**: $ARGUMENTS

- Format: `<task description, plan file path, or issue reference> [options]`
- Examples:
  - `Issue 123456 — wire the overwrite-existing-records flag through to the import pipeline`
  - `Plans/my-existing-plan.md` in the notes folder goes straight to Phase 2 with this plan. Phase 1 still runs briefly to load earlier context.
  - `Fix the SingleOrDefault() 500 in InvoiceValidator --rounds=3`
  - `Create a worktree jdoe/tasks/123456-overwrite-existing-records from release/2.0, then follow this skill's workflow.` names the branch and the base branch, so Phase 0 does not derive a branch name.
- If $ARGUMENTS is empty, use the **AskUserQuestion** tool to ask what to work on.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`, `master`, or `develop`. |
| `--branch-prefix=<prefix>` | derive from context, else ask | The prefix of the task-branch name of Phase 0. Use the first of these that gives a prefix: this flag, a branch-naming rule in the `CLAUDE.md` of the repo, the configured branch prefix, a branch-naming rule in the `CLAUDE.md` of the user. If none gives a prefix, ask the user once per run, before you create the branch. |
| `--commit-mode=<per-phase\|single>` | `per-phase` | `per-phase`: one commit after Phase 2 (Implement), then the commits of each Phase 3 round. `single`: run every phase and every review round the same way, but squash the whole run into **one commit at the end** (see "Commit cadence"). |
| `--rounds=<N>` | `2` | Review-loop cycles. Passed to `dev-essentials:review-loop` as `--rounds`. |
| `--context=<path>` | auto | A research or handoff file to load, instead of fresh research or in addition to it. The resolution is the same as for the `--context` of `dev-essentials:implement`. **Repeatable**: the run reads every path, and no path replaces another. |
| `--skip-research` | off | Skip Phase 1, for example to resume a session whose plan exists and is current. Phase 2 still loads each `--context`. |
| `--mode interactive\|partial\|full` | `partial` | The work mode. `dev-essentials:work-modes` defines the modes, and the gate table in "Autonomy" says what each mode does here. |

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the three modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Before Phase 0: the GitHub repository of the pull request | Find it at the final gate, before its question | Same | Find it now, as "The repository" in `references/finish.md` of `dev-essentials:work-modes` says. When another workflow runs this skill, or that file says to do no step, skip this row |
| Phase 0 step 2: branch pattern for an issue of unknown type | Use the `tasks` pattern, and say so | Ask | Same as partial |
| Phase 1 step 4: plan sign-off | Report the plan path, and start Phase 2 | Wait for sign-off | Same as partial |
| Phase 1 step 4: open decisions of the plan | Ask them all in one message | Ask | Decide, and write each one into the plan |
| Commit cadence, single mode: the squash script refuses (exit code 3) or cannot run (exit code 2, or no `RESULT` and no `OLD HEAD` line) | Stop and ask | Same | Skip the squash, and report it |
| Commit cadence, single mode: the squash script fails (`RESULT: FAILED`, or an `OLD HEAD` line and no `RESULT` line) | Stop and ask | Same | Stop and ask |
| Phase 3: review loop | Its gates, with the mode of this run | Same | Same |
| Phase 4: `save-context` cleanup of a file of an older session or a stale branch | Ask once, after the report | Same | Keep the files and the branches, and list them in the report |
| Phase 5: push, pull request, and merge | Ask one question after the report | Same | No stop. A failed step ends the run with a report |
| Fable on the own initiative of the agent | Move up by the model ladder, and name the step in the final report | Ask before each Fable dispatch | Same as partial |

Phase 5 holds the push, the pull request, and the merge. When another workflow runs this skill, Phase 5 does not run, and that workflow does the finish steps at its own end.

## Subagent dispatch

Read `dev-essentials:subagent-orchestration` before the first dispatch. Its rules apply to every dispatch, and this skill adds these:

- **Models**: fact gathering in a Phase 1 subagent uses Haiku, through the agent type `dev-essentials:fact-gatherer`. A Phase 1 question that needs judgment goes to a researcher on Opus. Planning (Phase 1) and review (Phase 3) use Opus. An implementer subagent of Phase 2 and a fixer subagent of Phase 3 use Sonnet. If a task that the plan gives as an explicit 1-2-3 edit list goes to a subagent, that subagent uses Haiku. A code search that a test of Rule 1 sends to a subagent uses Haiku, through `dev-essentials:code-locator`. This line is the one home of these models, and the phases below name only the role. All follow "Model selection" in `dev-essentials:subagent-orchestration`.
- **Effort**: pass `effort` on each dispatch of a general agent type. A Phase 1 researcher and the planner: `high`. The planner of a large plan, or of a change on the critical path: `xhigh`. A Phase 2 implementer: `high`. For a task that the plan gives with its exact files and edits, use `medium`. An edit-list implementer: `low`. `dev-essentials:review-loop` sets the effort of the reviewer and of a fixer subagent of Phase 3 with its `--reviewer-effort` and `--fixer-effort` options. This line is the one home of these effort levels.

## Guardrails

- **Do not improvise**. If the right resolution of a research finding, a plan ambiguity, or a review finding is unclear, ask the user. Do not guess. In the full mode, decide as `dev-essentials:work-modes` says.
- **Own every red signal** from the build and test steps of Phase 2 and Phase 3 in this session (`dev-essentials:engineering-discipline` Rule 1). Never call one "pre-existing", and do not search the history to find out whether it predates this run.
- **Push only in Phase 5.** The file `references/finish.md` of `dev-essentials:work-modes` gives the approval rules of the push.

## Progress tracking for the user

Keep a task list with one entry for each phase (Research & Plan, Implement, Review loop, Report), and update it. After Phase 2 knows the tasks, add one entry for each task. Use `TodoWrite`, or `TaskCreate`, `TaskUpdate`, and `TaskList`, whichever this session has. Without such a tool, use the boxes of the plan file and a short status line at the top of each reply. The list is for the user only, never for coordination between subagents. The plan file stays the source of truth.

## Phases

A request to finish an earlier run of this skill goes straight to Phase 5, as "Resume" in its file `finish.md` says.

### Phase 0 — Branch & worktree setup

0. **A worktree and branch that already exist: verification only.** Case: the caller says that the worktree and the branch exist, and gives the branch name and the absolute worktree path. A wrapper such as `dev-essentials:implement-task` does exactly this. In this case, Phase 0 is only a verification step: find out whether `git -C "<worktree path>" rev-parse --abbrev-ref HEAD` prints the expected branch.
   - If it does, skip steps 1 to 3, and run every later phase in that worktree. Do **not** derive a branch name again, and do **not** create a second worktree or branch.
   - If it does not, stop and ask the caller or the user. Do not create a branch or a worktree to recover.
   - If the caller gave no worktree or branch, go on with step 1.
1. Resolve the **base branch** as the `--base` row of the Options table says.
2. Resolve the **task branch name**. If $ARGUMENTS names a branch (as in the worktree example of "Arguments"), use it verbatim. Else resolve `--branch-prefix` first (see the Options table). Then build the name from that prefix and the issue reference in $ARGUMENTS, by the type or label of the GitHub issue:

   | Source | Branch name pattern | Example (`--branch-prefix=jdoe`) |
   | --- | --- | --- |
   | GitHub issue typed/labeled `task` | `<branch-prefix>/tasks/<ID>-<short-description>` | `jdoe/tasks/123456-add-invoice-pagination` |
   | GitHub issue typed/labeled `bug` | `<branch-prefix>/bugs/<ID>-<short-description>` | `jdoe/bugs/123456-fix-timeout` |
   | GitHub issue, any other type/label `<type>` | `<branch-prefix>/<type>s/<ID>-<short-description>` | `jdoe/features/123456-add-x` |
   | Research (no issue at all) | `<branch-prefix>/researches/<short-description>` | `jdoe/researches/investigate-y` |

   `<ID>` is the issue number from $ARGUMENTS. For example, `Issue 123456` or `#123456` gives `123456`. The research pattern has no `<ID>` part. `<short-description>` is a short kebab-case slug of the task description. If the type or label of the issue is unknown and the task is not research, do this. Outside the interactive mode, use the `tasks` pattern, and say so in the final report. In the interactive mode, ask the user which pattern applies, and do not guess.
3. If $ARGUMENTS asks for a worktree (for example "Create a worktree ... from ..."), create it with `dev-essentials:git-worktree-management`, from the base branch of step 1 and with the branch name of step 2. Else create the branch, or check it out, as `dev-essentials:git-sync` says.
4. Run every later phase in that branch or worktree.

### Phase 1 — Research & Plan

With `--skip-research`, skip this phase.

If $ARGUMENTS is a plan file, run only step 1 (load the context), and use that plan file as the plan of this run. Skip steps 2 and 3, and do not save a new plan in step 4. Still apply the sign-off and the open-decision bullets of step 4 to that plan file, then start Phase 2.

1. Resolve each `--context=<path>` (the flag is repeatable). Without one, derive a context file as `dev-essentials:implement` does: from a plan-file argument, or from the auto-memory folder as a last fallback. Read all of them in the orchestrating session before any dispatch. Pass their findings verbatim into every brief of this phase.
2. Find the facts by the tests of Rule 1 of `dev-essentials:subagent-orchestration`. For a small task, look them up in the main loop. For questions that are independent and that each read many files, dispatch fact gatherers in parallel. Give each one narrow question, in one message (Rule 3). The research works from the real code, not from assumptions. The research finds out what already exists, which files are involved, which patterns the code around it uses, and what is unclear or open. For example: one question on the production code path, one on the test coverage, and one on the callers of a method that the task changes. Each brief holds the question, the absolute worktree path, and the scope. It also holds the context of the user verbatim and each rule of the project `CLAUDE.md` that matters. A question that needs judgment goes whole to a researcher, not to a fact gatherer. Examples: an ambiguous change of behavior, a permission, a public contract, or a choice between designs. The researcher gets the same brief, and returns its findings with `path:line` evidence.
3. When the facts of step 2 are in, dispatch a planner. Paste each report, or the facts that the main loop found, verbatim into its brief. The planner reads only the lines that a critical decision of the plan depends on, and does no new broad research. If it needs a location that no report holds, it can dispatch `dev-essentials:code-locator` for it. It turns the research into a concrete plan: ordered tasks or phases, and for each task the exact paths, the anchors (`path:line` and method names), and the key signatures. The plan also lists the open decisions. An open decision is a critical decision that the task, the code, and the documentation do not settle. Examples: an ambiguous change of behavior, or a change of a public contract. Also anything that the current spec or plan does not cover (`dev-essentials:engineering-discipline` Rule 2).
4. Save the plan to the location that the `CLAUDE.md` of the repo documents. Else save it to `Plans/<slug>-plan.md` in the notes folder. This is the plan sign-off gate:
   - Outside the interactive mode, report the plan path in one status line, and start Phase 2.
   - In the interactive mode, **show the plan to the user for sign-off before Phase 2 starts**. Resolve here each open question that the user raises.
   - If the plan lists open decisions, handle them before Phase 2. Outside the full mode, ask them all in one message, and start Phase 2 after the answers. In the full mode, decide them as `dev-essentials:work-modes` says, write each decision into the plan, and start Phase 2.

   Do not carry ambiguity into Phase 2.

### Phase 2 — Implement

1. Load the plan from Phase 1, the plan file of the argument, or `--context` for a resumed session. Both shapes of `--context` must work here, not only be accepted:
   - **Plan-shaped** (it has a task checklist): use it as it is.
   - **A research or handoff file without a checklist**: derive a task list from its content. Do not refuse the file.
   - **Several `--context` paths**: a plan-shaped file gives the task list, and the others are research context. Without a plan-shaped file, derive the task list from all of them.
2. For each task or phase of the plan, use the tests of Rule 1 of `dev-essentials:subagent-orchestration`. Implement a small task in the main loop. For a task that passes a test, dispatch an implementer subagent with the brief rules of `dev-essentials:implement` Step 4. Follow the existing patterns, ask and do not improvise, and use the skills that fit the change type (domain models, tests, controllers, configuration, and others). An explicit 1-2-3 edit list gives the path, the old text, and the new text. If such a task goes to a subagent, dispatch an edit-list implementer for it.
3. Mark each task done in the plan file as it completes (`- [ ]` → `- [x]`).
4. Build and test. The one who implements a task runs its build and tests, so that it sees each red signal and fixes it. An implementer subagent reports the verbatim result lines. Before each commit of this phase, run the build and the tests one time in the main loop. Item 1 of the section `Trust but verify` in `dev-essentials:subagent-orchestration` says how. A green run of the main loop after the last edit is that run. If a result differs from a report, or the run is red, fix it or resume the implementer with the error lines. Then run again. Never leave a red signal for the review loop.
5. For the commits of this phase, see "Commit cadence".

### Phase 3 — Review loop

Invoke `dev-essentials:review-loop` on the output of Phase 2: `target=branch` in the common case, or `target=diff <range>` to review only part of the work. Do not reimplement its mechanics. Its section "Default configuration" is what this skill wants, so override nothing. Pass only these options of this skill:

- `--rounds=<N>` from the `--rounds` of this skill (default `2`).
- The `--mode` of this run.

Record each finding that the user and the orchestrating session agree to defer, as deferred in the Phase 4 report. "Commit cadence" says how the commits of each loop round fit the commit mode.

### Phase 4 — Report

Write the handoff document with `dev-essentials:save-context`, and follow all of its steps. Pass the path `Results/<slug>-report.md` in the notes folder as its path argument. Pass no flag. This also applies to `--plan` and to the `--mode` of this run. It is an exception to the rule of `dev-essentials:work-modes` that passes the mode on. `save-context` finds the plan of Phase 1 in the conversation (its Step 1). So `save-context` runs in its partial mode, also in a run in the full mode. It runs its Step 5 cleanup and prints no continuation prompt. Outside the full mode, its Step 5 asks the user before it moves a file of an older session to the backup. In the full mode, tell the cleanup to keep each file of an older session and each stale branch. It lists them as kept, and it asks no question. If another command follows the steps of `save-context`, the cleanup runs only when that command asks for it. This phase is the last local step of the run, so ask for the cleanup. Also tell the cleanup to keep every file of this run, except a `_`-prefixed progress file whose task is done. These are the plan, the review reports, the report, and each context document of a wrapper such as `implement-task`. The branch of this run is not merged, and the user still reviews it. If the repo documents its own path, use that. For a run that continues a numbered session sequence of the user, use a `-handoff-N.md` name. The report has these sections:

- **Overview**: what this run covered, the branch, the base branch, the head commit at the end of the run, the worktree, and the date.
- **What Was Done**: for each phase, the research findings, the plan, each implemented task, and the outcome of each review round.
- **Key Decisions**: a table with the reasons. It holds each decision that Phase 1 or Phase 3 asked the user to sign off. It also holds each gate that this run passed without a stop. In the full mode, also list each decision that the run made for the user under "Decisions for your review".
- **Issues Found**: what this run found but did not cover, candidate follow-up issues, and each process problem to report to the user.
- **Key File Paths**: grouped by category (core, tests, configuration, docs).
- **What's Next**: the remaining work. The branch is not pushed yet. Say whether Phase 5 runs next, or whether the calling workflow does the finish steps.

Tell the user where the report is. Give the same one-line summary as `save-context`, and say what its Step 5 cleanup did. Also give the final verdict of the review loop (`stop-clean`, `stop-max-rounds`, or `stop-blocked`). Print the report only, and end it with the `Route:` line of Rule 1 of `dev-essentials:subagent-orchestration`. Outside the full mode, Step 5 can list files or branches that wait for the yes of the user. If it does, ask its one Step 6 question after the report. In the full mode, ask no question, and list the kept files and branches in the report. When the user says yes, move the listed files to the backup in this session, as Step 5 of `save-context` says. If the user asks for a continuation prompt in this run, print it last. Else print no continuation prompt for the next session.

### Phase 5 — Finish (push, pull request, merge)

When another workflow runs this skill, skip this phase. Examples are `dev-essentials:implement-task` and the `deep-fix` of `dev-essentials:process-pr-comments`. That workflow does the finish steps at its own end.

Else read `${CLAUDE_PLUGIN_ROOT}/skills/work-modes/references/finish.md`, and do its steps on the branch of this run. The base branch is the base of Phase 0, and the verdict of the review loop is the verdict of Phase 3. In the partial mode and in the interactive mode, ask the question of its final gate after the Phase 4 report.

## Commit cadence

### Per-phase mode (default)

- **After Phase 2 completes** (all tasks of this run implemented, built, and tested green), make one commit. If the plan has several independent tasks, one commit for each task is also fine. Follow the structure of the plan. Never go into Phase 3 with uncommitted Phase 2 output.
- **During Phase 3**, the review loop commits once per round by default. Do not suppress this.

### Single-commit mode (`--commit-mode=single`)

- Before Phase 2 starts, record the SHA of `HEAD` as `RUN_BASE_SHA`.
- Run Phase 2 and Phase 3 as described above. Commit the Phase 2 output before Phase 3 starts, as in per-phase mode. Phase 3 keeps the normal round commits of the review loop. Do not suppress them with `--dry-run` or `--no-verify-fix`. Both flags also skip the fix itself.
- The session makes each Phase 2 commit, so the brief of an implementer subagent tells it not to commit. Stage explicit paths, never `git add -A` or `git add .`. Never stage the plan file of this run, because the squash script refuses a plan file in the commits.
- Record the SHA of each commit of this run in `RUN_COMMITS`: each Phase 2 commit, and each commit that the review loop makes. Run `git rev-parse HEAD` right after each commit.
- After Phase 3, and **before** the Phase 4 report, squash the whole run into one commit on `RUN_BASE_SHA` with the script `squash_task.py` of this plugin. It needs Python 3 and git. On Windows, run it in the Bash tool (Git Bash). `--repo` is the absolute path of the work tree of this run. Give one `--commit` for each SHA of `RUN_COMMITS`. Give the folder of the plan file of this run as `--plan-dir`. If the run has no plan file, or if the plan file is at the root of the work tree, leave out `--plan-dir`. If git tracks a plan file at the root of the work tree, Phase 2 changes it. Then the script refuses with a `CHANGED` line for it. Handle that refusal as the list below says. The message sums up the implementation and the fixes of each review round:

  ```bash
  python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/squash_task.py" --repo "<work tree>" --plan-dir "<plan folder>" --base <RUN_BASE_SHA> --commit <sha> --commit <sha> --message "<Issue ref> — <summary> (implement + <N> review rounds)" --apply
  ```

  - Take the SHAs from the commits that this run made, never from `git log` of the range. A list from the log hides the commit of someone else.
  - The script makes each check before the squash. It refuses a commit of the range that is not a `--commit`, and a merge commit. It also refuses a changed tracked file, a staged plan file, a detached HEAD, and a plan file in the commits. A refusal changes nothing.
  - `RESULT: REFUSED` (exit code 3) is the squash-base safety stop. **Stop and ask the user**, and show the `REFUSED`, `COMMIT`, `MISSING`, `CHANGED`, and `PLAN FILE` lines. Never squash across the commit of someone else. In the full mode, do not stop. Skip the squash, keep the commits as they are, and report the refusal.
  - `RESULT: ONE COMMIT`: the run made only one commit, so it needs no squash. The script makes no commit. Say so.
  - `RESULT: SQUASHED`: the `NEW` line gives the SHA of the run commit. Report each `WARN` line.
  - `RESULT: FAILED` (exit code 1), for example after a failed commit hook: the script put the old HEAD back. Show the `FAILED` and `OUTPUT` lines to the user, and ask. If the `RESULT` line says `NOT RESTORED`, first run `git -C "<work tree>" reset --soft <OLD HEAD>`. After a `RESTORED` line, this command changes nothing.
  - An `OLD HEAD` line and no `RESULT` line: an error, for example Ctrl+C, stopped the script after it moved the branch. This output has no `OUTPUT` line, so show the last line of the error output to the user, and ask. After a `RESTORED HEAD` line, the old HEAD is back and nothing needs an undo. With no `RESTORED HEAD` line, the restore failed: show the output to the user, and give the command `git -C "<work tree>" reset --soft <OLD HEAD>`.
  - If `python3` is not available, or the script exits with code 2, keep the commits as they are, and ask the user. If the output has no `RESULT` line and no `OLD HEAD` line, do the same. In the full mode, report the problem instead.
- **The `stop-blocked` exception**. If the review loop ends with `stop-blocked`, do not squash. Keep the round commits as they are, so that the caller can inspect the red state, and report the verdict.
- A caller can run this mode on a branch where others can also commit, for example a shared PR branch. That caller must make sure that nothing else commits between `RUN_BASE_SHA` and the squash. This skill does not coordinate it for the caller.
