---
description: Work one task end-to-end with research, a plan, the implementation, a review, and a report. Sweep the extra context first (PR or issue links, notes), and add a /simplify commit at the end.
argument-hint: <issue reference or task description> [--base=<branch>] [--worktree=<branch-ref>] [--no-worktree] [--refs=<url|id|text>...] [--commit-mode=per-phase|single] [--rounds=N] [--notes-dir=<path>] [--no-simplify] [--mode interactive|partial|full]
---

# Implement Task (context sweep → full cycle → simplify commit)

## Division of labor in this command family

- `dev-essentials:implement` runs the tasks of an existing plan file, with no research and no review loop.
- `dev-essentials:research-implement-review-report` (RIRR) works one task: research, a plan, the implementation, a review loop, and a report.
- `dev-essentials:implement-task` wraps RIRR for one task. It adds a sweep of extra context first and a `/simplify` commit at the end.
- `dev-essentials:implement-batch` works N related tasks in one branch: one squashed commit for each task, then one final review across the tasks.
- `dev-essentials:feature-pipeline` runs one task end-to-end in an isolated git worktree. The task is a tracked task of the task provider (for example, GitHub Issues or Jira), or a plain request. Subagents run its stages from the requirements to the reviews, the session pushes and opens the PR, and it has its own approval gates.

This command owns only the order of the phases, the worktree, the context sweep (Phase 2), and the `/simplify` commit (Phase 4). It also owns the finish steps (Phase 6). Do not reimplement RIRR, `/simplify`, or `dev-essentials:git-worktree-management`.

The configured branch prefix is `${user_config.branch_prefix}`. If the value still shows as a `${...}` placeholder, no value is saved, and the configured branch prefix is empty. The notes folder is the folder that `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md` gives. Read that file before the first read or write in the notes folder.

**Arguments**: $ARGUMENTS

- Format: `<issue reference or task description> [options]`
- Examples (no value in them is fixed behavior):
  - `Issue 123456: add pagination support to the invoice export endpoint --base=main --refs=https://github.com/acme/billing-service/pull/482 --refs=1201`
  - `Issue 456789: add the retry option --base=release/2.0 --refs=https://github.com/acme/payments-service/pull/641 --refs="follow the retry pattern of the notification client"` (a PR link and a free-text note in one list)
- The context list is optional and can have any number of items, in any order, from any repo or tracker. With zero items, Phase 2 does nothing and says so.
- If $ARGUMENTS is empty, use the **AskUserQuestion** tool to ask what to work on.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`, `master`, or `develop`. |
| `--worktree=<branch-ref>` | ask or derive | Use the ref that this flag or the prose of $ARGUMENTS names, verbatim. Else build it with the branch-name table in Phase 0 of RIRR. Take `<prefix>` from the first of these that gives one: a branch-naming rule in the `CLAUDE.md` of the repo, the configured branch prefix, a branch-naming rule in the `CLAUDE.md` of the user. If none gives a prefix, **ask once**. With `--no-worktree`, the ref names only the branch that Phase 1 creates, so resolve it only then. |
| `--no-worktree` | off | Make no worktree, and work on the current branch in the current folder. Phase 1 says what the run does on the default branch, the base branch, or a detached HEAD. |
| `--refs=<url\|id\|text>` | none | Extra context, repeatable, added to the references in the prose. A value is **a URL or an ID** (a PR, an issue, a document, or a wiki page). Or it is **plain free text** with nothing to fetch. The way that a value reads decides its kind, not a tag. Read-only (see Phase 2). |
| `--commit-mode=<per-phase\|single>` | `single` | Passed verbatim to the `--commit-mode` of RIRR. RIRR defaults to `per-phase`. This command defaults to `single`, because the goal is one task commit plus one simplify commit. Both modes work (see Phase 4). |
| `--rounds=<N>` | `2` | Review-loop cycles. Passed verbatim to the `--rounds` of RIRR. |
| `--notes-dir=<path>` | the notes folder | The folder for the files of this run: `Research/` (Phase 2 context document), `Plans/`, and `Results/`. |
| `--no-simplify` | off | Skip Phase 4. Use it only for a run in which the user does not want the pass. |
| `--mode interactive\|partial\|full` | `partial` | The work mode. `dev-essentials:work-modes` defines the modes, and the gate table in "Autonomy" says what each mode does here. |

The other options of RIRR (`--context`, `--skip-research`, and `--branch-prefix`) pass through. For `--context`, see Phase 3.

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Before Phase 0: the GitHub repository of the pull request | Find it at the final gate, before its question | Same | Find it now, as "The repository" in `references/finish.md` of `dev-essentials:work-modes` says. When that file says to do no step, skip this row |
| Phase 1: `--no-worktree` on the default branch, the base branch, or a detached HEAD | Ask for a branch name. On a branch, also offer a yes to work on it, with local commits and no finish step | Same | Create the branch of the `--worktree` row, and name it in the final report |
| Phase 2: a reference that implements or contradicts the task | Ask before Phase 3 | Same | Same |
| Phase 3: RIRR | Its gates, with the mode of this run | Same | Same |
| Phase 4 step 3: a cleanup that needs a change of behavior | Stop that cleanup, and put the question in the report | Same | Keep the code, and list the skipped cleanup |
| Phase 5: `save-context` cleanup of a file of an older session or a stale branch | Ask once, after the report | Same | Keep the files and the branches, and list them in the report |
| Phase 6: push, pull request, and merge | Ask one question after the report | Same | No stop. A failed step ends the run with a report |
| Fable on the own initiative of the agent | Move up by the model ladder, and name the step in the final report | Ask before each Fable dispatch | Same as partial |

## Subagent dispatch

Read `dev-essentials:subagent-orchestration` before the first dispatch. Its rules apply to every dispatch. A bare "Rule N" in this file is one of them. This command adds these:

- The orchestrating session resolves the arguments, asks the Phase 0 questions, creates the worktree, dispatches, and reads the reports. It also writes the Phase 2 context document, does the git bookkeeping (SHA records and the Phase 4 commit), and talks to the user.
- It does not fetch a PR or an issue, or review a diff. Outside Phase 3, it does not edit product code. The Phase 2 subagents and the Phase 4 subagent do that work. In Phase 3, RIRR decides by its own rules which work runs in the main loop. Pass the context of the user verbatim (Rule 2).
- Each brief asks for a short structured report: verdicts, `file:line` anchors, and the commands that ran with their real results. Never ask for pasted diffs, file dumps, or comment HTML.
- Phase 2 names its models, and RIRR keeps its own. All follow "Model selection" in `dev-essentials:subagent-orchestration`.
- A bounded dispatch (one reference to read, one simplify pass) does the work itself (Rule 7). Write into the brief: "Do this work yourself. Do not dispatch further subagents for it."

## Guardrails

- **Context is context, never a target.** Never change, comment on, or vote on a fetched reference. The task does not fix what a fetched reference left undone, unless the user asks.
- **Own every red signal** from each build or test run in this session. This includes Phase 4 (`dev-essentials:engineering-discipline` Rule 1). Never call one "pre-existing", and do not search the history to find out whether it predates `RUN_BASE_SHA`.
- **The files of this run live under `<--notes-dir>`**, never at the root of the repo. Never reference them from shipped code, docs, or commit messages (`dev-essentials:engineering-discipline` Rule 3).

## Progress tracking for the user

Keep a task list with one entry for each phase, and update it as each phase runs. Use `TodoWrite`, or `TaskCreate`, `TaskUpdate`, and `TaskList`, whichever this session has. The list is for the user only, never for coordination between subagents.

## Phases

A request to finish an earlier run of this command goes straight to Phase 6, as "Resume" in its file `finish.md` says.

### Phase 0 — Resolve the ask

1. Take these items from $ARGUMENTS verbatim: the task, the base branch, the worktree branch ref, every context item (from `--refs` and from the prose), and each scope guard of the user. Sort the context items as the `--refs` row says. Pass all of it verbatim into every brief.
2. Resolve `--base` and `--worktree` as the Options table says.
3. Before any work, echo one short block: the task, the base branch, the worktree branch ref or `--no-worktree`, the context list, the commit mode, and whether the simplify pass runs.
4. If a material fact is missing or unclear, ask with the **AskUserQuestion** tool before any work. Examples: the task, the branch, the worktree name, which of two readings applies, or whether a link is context or the thing to change. If nothing is unclear, start without a round of approval.

### Phase 1 — Worktree setup

Without `--no-worktree`, create the worktree from the Phase 0 base branch with `dev-essentials:git-worktree-management`, and run its post-create bootstrap. Record the absolute worktree path.

With `--no-worktree`, make no worktree. Read `${CLAUDE_PLUGIN_ROOT}/skills/work-modes/references/no-worktree.md` before any other step of Phase 1, and do its steps. They keep the work of the user in the current folder safe. In that file, the base branch is the Phase 0 base branch.

Each write-capable dispatch from here on carries the worktree path (Rule 6), and each git call uses `git -C "<abs worktree path>"`.

Then record `RUN_BASE_SHA = git -C "<worktree>" rev-parse HEAD` for Phase 4 and Phase 5.

### Phase 2 — Additional context sweep (skipped when none is given)

With zero context items, say so in one line, write no document, and go to Phase 3.

Dispatch **Opus** subagents to fetch the URLs and IDs. For one fetchable item or none, use one subagent. For independent items (different repos, unrelated issues or pages), use one subagent each, in parallel (several `Agent` calls in one message). A pure extraction with no synthesis can use **Haiku**, for example the title and description of an issue.

Each brief contains:

- The absolute worktree path, the base branch, the task text verbatim, and the context list verbatim, with each item marked as fetchable or free text.
- **Read-only: do not edit, create, or delete any product file. Do not create, comment on, update, or vote on any PR, issue, or document. Write no file.**
- Access (Rule 4): use the MCP or web-fetch tool of the host of the item. For GitHub, load `dev-essentials:github-mcp-conventions`. For a host without a fetch tool, stop that item, and name it in the report as not fetched. The orchestrator then asks the user. Never skip the item silently or fall back to raw REST calls. **Never fetch a free-text item.** Carry it through verbatim.
- The report, in the final message only, with these groups and a synthesis:
  - **Fetched references**, one section each: what it is, its author, its state (merged, active, or abandoned, and open or closed), and its intent in one paragraph. Then the files and types that it touched, with `file:line` anchors into the base branch, and the ones in the area of this task.
  - **Free-text notes**, each quoted verbatim, with no invented author, state, or files.
  - One synthesis over both groups. **The pattern established**: the shape of a consistent implementation, concrete enough to plan against. **Constraints and conflicts**: what limits the task or contradicts its text, and for a fetched reference, work in flight that can collide. **Explicitly out of scope**: what a fetched reference already does, which this task must not do again.
- A stop rule: an item that already implements the task, or contradicts it, goes to the user before Phase 3. Do not resolve it alone.

When every dispatch is back, write `<--notes-dir>/Research/<slug>-context.md` in the orchestrating session, with the summaries and the free-text items in the same groups. Never delegate this write (Rule 1). Show the user the summary in a few lines, with each conflict.

### Phase 3 — Run the wrapped workflow, through its review loop

Invoke `dev-essentials:research-implement-review-report`. Its Phases 0 to 3 run as written, with its own plan gate, review-loop configuration, and commits. **Do not reimplement, reorder, or second-guess any of it.** Pass:

- The task text from Phase 0, verbatim.
- `--base=<Phase 0 base branch>`, the branch name, and the absolute worktree path, with this instruction: **its Phase 0 is only a verification step**. The worktree and the branch exist, so it must not create or derive a branch or a worktree.
- With `--no-worktree`, the files of the user from Phase 1, and the rule that no task writes, stages, or deletes one of them.
- `--commit-mode=<resolved>`, `--rounds=<N>`, and the `--mode` of this run.
- `<--notes-dir>` as the artifact root, in words, because RIRR has no such flag. The `Plans/` and `Results/` folders that RIRR keeps in the notes folder move under it. For RIRR, it is the notes folder that the request names (item 1 of `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md`).
- `--context=<--notes-dir>/Research/<slug>-context.md`, **only for a document that Phase 2 wrote**. Never pass a path that does not exist. Also pass each `--context` of the user. The Phase 2 document never replaces it. Require this: pass the findings of the document verbatim into every brief of its Phase 1 and into the "Findings" section of the plan.
- **A hard stop: finish Phase 3 (the review loop) and, in `single` mode, the squash. Then stop and return control. Do not start Phase 4 (Report).** Phase 4 of this command runs between the two, and the squash must not take in its commit.

When RIRR returns, record `SIMPLIFY_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.

### Phase 4 — Mandatory simplify pass (its own commit)

Skip this phase only with `--no-simplify`. `/simplify` is an external skill that cleans up changed code. It does not hunt for bugs.

1. Dispatch one subagent that runs `Skill(skill: "simplify")` (or `/simplify`) exactly once on `<RUN_BASE_SHA>..HEAD` in the worktree, and then does steps 2 to 4. Name the range in the call, because the skill defaults to "the changed code" and this run is already committed. One pass, not a loop.
2. Tell the skill to look for complexity that this run added. Examples: a guard that no failure needs, an abstraction with one caller, logic that a helper already covers, useless indirection, or code at the wrong altitude.
3. Scope: a simpler diff with the same behavior. Out of scope: code that this run did not change, and a change of behavior or of a public contract. Also out of scope: a deleted or weaker test, and a swallowed error path. If a cleanup needs one of these, stop that cleanup. Put the question in your report, so that the caller asks the user (`dev-essentials:engineering-discipline` Rule 2). In the full mode, keep the code and list the skipped cleanup in the report.
4. Build and test again. A test that the cleanup breaks is a regression of this session (Rule 1 of the same skill). For .NET, follow `dev-essentials:dotnet-build-test`.
5. When the subagent reports, read the verbatim result lines of its build and test run. Then run the build and the tests one time in the worktree, as item 1 of the section `Trust but verify` in `dev-essentials:subagent-orchestration` says. If the result differs from the report, or the run is red, resume the subagent with the error lines. Do not commit before the run is green.
6. Commit the cleanup as **a separate commit on top**. Stage explicit paths, never `git add -A` or `git add .`.

   ```bash
   git -C "<worktree>" commit -m "<Issue ref> — simplify: <summary of cleanups>"
   ```

   In `single` mode, it goes on top of the squashed commit. **Never `--amend` into that commit, and never squash again.** The end state is two commits. In `per-phase` mode, it goes on top of the phase and review-round commits.
7. A pass that changes nothing is valid. Make no empty commit and invent no cleanup. Report "simplify pass found nothing worth changing" and go on.

### Phase 5 — Report

Return control to **Phase 4 (Report)** of RIRR. Tell it not to run its Phase 5 (Finish), because Phase 6 of this command does the finish steps. Phase 4 writes the report through `dev-essentials:save-context`, as the last local step of the run. The call passes no flag, so `save-context` runs in its partial mode. Its cleanup keeps every file of this run, also the Phase 2 context document. Outside the full mode, it asks the user before it moves a file of an older session to the backup. In the full mode, it keeps each file of an older session and each stale branch, and lists them (Phase 4 of RIRR). It prints no continuation prompt, unless the user asks for one in this run. Do not assume the default path `<--notes-dir>/Results/<slug>-report.md`. Take the path from the message in which that phase names it. Add to the report:

- The Phase 2 sweep: the items read, the pattern that they set, how the implementation followed it, each conflict and its resolution, and the path of the context document.
- The Phase 4 pass: ran or skipped, what it changed, its commit subject, and the real output of the build and tests after it.
- **The real commit topology**: `git -C "<worktree>" log --oneline <RUN_BASE_SHA>..HEAD`. In `single` mode, the expected result is **one task commit plus one simplify commit**, or only the task commit after an empty pass. If the result differs, report it and explain why. For Phase 4, `git -C "<worktree>" log --oneline <SIMPLIFY_BASE_SHA>..HEAD` must show exactly one commit, or zero after an empty pass.
- The absolute worktree path, the branch name, and the head commit at the end of the run.
- Each gate that this run or RIRR passed without a stop.

Print the report only, and end it with the `Route:` line of Rule 1 of `dev-essentials:subagent-orchestration`. Outside the full mode, Step 5 of `save-context` can list files or branches that wait for the yes of the user. If it does, ask its one Step 6 question after the report. In the full mode, ask no question. When the user says yes, move the listed files to the backup in this session, as Step 5 of `save-context` says. If the user asks for a continuation prompt in this run, print it last. Else print no continuation prompt for the next session.

### Phase 6 — Finish (push, pull request, merge)

Read `${CLAUDE_PLUGIN_ROOT}/skills/work-modes/references/finish.md`, and do its steps in the worktree. With `--no-worktree`, the worktree is the folder of the user, so remove no worktree in item 3 of Step 4 of `dev-essentials:merge-pr`. If the run has `--no-worktree` and a linked worktree holds the branch, also keep the branch. Name both in the finish report. The base branch is the Phase 0 base, and the verdict of the review loop is the verdict that RIRR reported. In the partial mode and in the interactive mode, ask the question of its final gate after the Phase 5 report.
