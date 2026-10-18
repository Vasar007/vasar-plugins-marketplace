---
description: Work one task end-to-end with research, a plan, the implementation, a review, and a report. Sweep the extra context first (PR or issue links, notes), and add a /simplify commit at the end. Pushes only with --push.
argument-hint: <issue reference or task description> [--base=<branch>] [--worktree=<branch-ref>] [--refs=<url|id|text>...] [--commit-mode=per-phase|single] [--rounds=N] [--notes-dir=<path>] [--no-simplify] [--push] [--interactive] [--autonomous]
---

# Implement Task (context sweep → full cycle → simplify commit)

## Division of labor in this command family

- `dev-essentials:implement` runs the tasks of an existing plan file, with no research and no review loop.
- `dev-essentials:opsx-implement` implements phases of an existing OpenSpec change, with no research and no review.
- `dev-essentials:research-implement-review-report` (RIRR) works one task: research, a plan, the implementation, a review loop, and a report.
- `dev-essentials:implement-task` wraps RIRR for one task. It adds a sweep of extra context first and a `/simplify` commit at the end.
- `dev-essentials:implement-batch` works N related tasks in one branch: one squashed commit for each task, then one final review across the tasks.
- `dev-essentials:feature-pipeline` runs a tracked task from the task provider (for example, GitHub Issues or Jira) end-to-end in an isolated git worktree. It has one subagent for each stage and its own approval gates.

This command owns only the order of the phases, the worktree, the context sweep (Phase 2), and the `/simplify` commit (Phase 4). Do not reimplement RIRR, `/simplify`, or `dev-essentials:git-worktree-management`.

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
| `--worktree=<branch-ref>` | ask or derive | Use the ref that this flag or the prose of $ARGUMENTS names, verbatim. Else build it with the branch-name table in Phase 0 of RIRR. Take `<prefix>` from the branch-naming convention in the `CLAUDE.md` of the repo or of the user. Without a convention, **ask once**. |
| `--refs=<url\|id\|text>` | none | Extra context, repeatable, added to the references in the prose. A value is **a URL or an ID** (a PR, an issue, a document, or a wiki page). Or it is **plain free text** with nothing to fetch. The way that a value reads decides its kind, not a tag. Read-only (see Phase 2). |
| `--commit-mode=<per-phase\|single>` | `single` | Passed verbatim to the `--commit-mode` of RIRR. RIRR defaults to `per-phase`. This command defaults to `single`, because the goal is one task commit plus one simplify commit. Both modes work (see Phase 4). |
| `--rounds=<N>` | `2` | Review-loop cycles. Passed verbatim to the `--rounds` of RIRR. |
| `--notes-dir=<path>` | `Notes/` | The root inside the worktree for the files of this run: `Research/` (Phase 2 context document), `Plans/`, and `Results/`. A convention in the `CLAUDE.md` of the repo wins. |
| `--no-simplify` | off | Skip Phase 4. Use it only for a run in which the user does not want the pass. |
| `--push` | off | Push after the final report. **Off unless the user asks for it in this invocation.** |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

The other options of RIRR (`--context`, `--skip-research`, and `--branch-prefix`) pass through. For `--context`, see Phase 3.

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

Read `dev-essentials:subagent-orchestration` before the first dispatch. Its rules apply to every dispatch. A bare "Rule N" in this file is one of them. This command adds these:

- The orchestrating session only resolves the arguments, asks the Phase 0 questions, creates the worktree, dispatches, and reads the reports. It also writes the Phase 2 context document, does the git bookkeeping (SHA records and the Phase 4 commit), and talks to the user.
- It never reads source code, fetches a PR or an issue, edits product code, or reviews a diff. A subagent does this work, also a small read (Rule 1). Pass the context of the user verbatim (Rule 2).
- Each brief asks for a short structured report: verdicts, `file:line` anchors, and the commands that ran with their real results. Never ask for pasted diffs, file dumps, or comment HTML.
- Phase 2 names its models, and RIRR keeps its own. All follow "Model selection" in `dev-essentials:subagent-orchestration`.
- Fable is for exceptional cases only. Never dispatch it silently on your own initiative. With `--interactive`, ask the user before each Fable dispatch, also where the model matrix allows Fable. Without `--interactive`, follow "Autonomy".
- A bounded dispatch (one reference to read, one simplify pass) does the work itself (Rule 7). Write into the brief: "Do this work yourself. Do NOT dispatch further subagents for it."

## Guardrails

- **Context is context, never a target.** Never change, comment on, or vote on a fetched reference. The task does not fix what a fetched reference left undone, unless the user asks.
- **Own every red signal** from each build or test run in this session. This includes Phase 4 (`dev-essentials:engineering-discipline` Rule 1). Never call one "pre-existing", and do not search the history to find out whether it predates `RUN_BASE_SHA`.
- **The files of this run live under `<--notes-dir>`** inside the worktree, never at the root of the repo. Never reference them from shipped code, docs, or commit messages (`dev-essentials:engineering-discipline` Rule 3).

## Progress tracking for the user

Keep a task list with one entry for each phase, and update it as each phase runs. Use `TodoWrite`, or `TaskCreate`, `TaskUpdate`, and `TaskList`, whichever this session has. The list is for the user only, never for coordination between subagents.

## Phases

### Phase 0 — Resolve the ask

1. Take these items from $ARGUMENTS verbatim: the task, the base branch, the worktree branch ref, every context item (from `--refs` and from the prose), and each scope guard of the user. Sort the context items as the `--refs` row says. Pass all of it verbatim into every brief.
2. Resolve `--base` and `--worktree` as the Options table says.
3. Before any work, echo one short block: the task, the base branch, the worktree branch ref, the context list, the commit mode, and whether the simplify pass runs.
4. If a material fact is missing or unclear, ask with the **AskUserQuestion** tool before any work. Examples: the task, the branch, the worktree name, which of two readings applies, or whether a link is context or the thing to change. If nothing is unclear, start without a round of approval.

### Phase 1 — Worktree setup

Create the worktree from the Phase 0 base branch with `dev-essentials:git-worktree-management`, and run its post-create bootstrap. Record the absolute worktree path. Each write-capable dispatch from here on carries it (Rule 6), and each git call uses `git -C "<abs worktree path>"`.

Then record `RUN_BASE_SHA = git -C "<worktree>" rev-parse HEAD` for Phase 4 and Phase 5.

### Phase 2 — Additional context sweep (skipped when none is given)

With zero context items, say so in one line, write no document, and go to Phase 3.

Dispatch **Opus** subagents to fetch the URLs and IDs. For one fetchable item or none, use one subagent. For independent items (different repos, unrelated issues or pages), use one subagent each, in parallel (several `Agent` calls in one message). A pure extraction with no synthesis can use **Haiku**, for example the title and description of an issue.

Each brief contains:

- The absolute worktree path, the base branch, the task text verbatim, and the context list verbatim, with each item marked as fetchable or free text.
- **Read-only: do not edit, create, or delete any product file. Do not create, comment on, update, or vote on any PR, issue, or document. Write no file.**
- Access (Rule 4): use the MCP or web-fetch tool of the host of the item. For GitHub, load `dev-essentials:github-mcp-conventions`. For a host without a fetch tool, stop that item, and name it in the report as not fetched. The orchestrator then asks the user. Never skip the item silently or fall back to raw REST calls. **Never fetch a free-text item.** Carry it through verbatim.
- The report, in the final message only, with two groups:
  - **Fetched references**, one section each: what it is, its author, its state (merged, active, or abandoned, and open or closed), and its intent in one paragraph. Then the files and types that it touched, with `file:line` anchors into the base branch, and the ones in the area of this task.
  - **Free-text notes**, each quoted verbatim, with no invented author, state, or files.
  - One synthesis over both groups. **The pattern established**: the shape of a consistent implementation, concrete enough to plan against. **Constraints and conflicts**: what limits the task or contradicts its text, and for a fetched reference, work in flight that can collide. **Explicitly out of scope**: what a fetched reference already does, which this task must not do again.
- A stop rule: an item that already implements the task, or contradicts it, goes to the user before Phase 3. Do not resolve it alone.

When every dispatch is back, write `<--notes-dir>/Research/<slug>-context.md` in the orchestrating session, with the summaries and the free-text items in the same two groups. Never delegate this write (Rule 1). Show the user the summary in a few lines, with each conflict.

### Phase 3 — Run the wrapped workflow, through its review loop

Invoke `dev-essentials:research-implement-review-report`. Its Phases 0 to 3 run as written, with its own plan gate, review-loop configuration, and commits. **Do not reimplement, reorder, or second-guess any of it.** Pass:

- The task text from Phase 0, verbatim.
- `--base=<Phase 0 base branch>`, the branch name, and the absolute worktree path, with this instruction: **its Phase 0 is only a verification step**. The worktree and the branch exist, so it must not create or derive a branch or a worktree.
- `--commit-mode=<resolved>`, `--rounds=<N>`, and the mode flag of this run: `--interactive`, `--autonomous`, or none.
- `<--notes-dir>` as the artifact root, in words, because RIRR has no such flag. Its `Notes/Plans/` and `Notes/Results/` move under it, as a convention of the repo that its Phase 1 and Phase 4 allow.
- `--context=<--notes-dir>/Research/<slug>-context.md`, **only for a document that Phase 2 wrote**. Never pass a path that does not exist. Also pass each `--context` of the user. The Phase 2 document never replaces it. Require this: pass the findings of the document verbatim into every Phase 1 research brief and into the "Findings" section of the plan.
- **A hard stop: finish Phase 3 (the review loop) and, in `single` mode, the squash. Then STOP and return control. Do not start Phase 4 (Report).** Phase 4 of this command runs between the two, and the squash must not take in its commit.

When RIRR returns, record `SIMPLIFY_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.

### Phase 4 — Mandatory simplify pass (its own commit)

Skip this phase only with `--no-simplify`. `/simplify` is an external skill that cleans up changed code. It does not hunt for bugs.

1. Dispatch one subagent that runs `Skill(skill: "simplify")` (or `/simplify`) exactly once on `<RUN_BASE_SHA>..HEAD` in the worktree, and then does steps 2 to 4. Name the range in the call, because the skill defaults to "the changed code" and this run is already committed. One pass, not a loop.
2. Tell the skill to look for complexity that this run added. Examples: a guard that no failure needs, an abstraction with one caller, logic that a helper already covers, useless indirection, or code at the wrong altitude.
3. Scope: a simpler diff with the same behavior. Out of scope: code that this run did not change, and a change of behavior or of a public contract. Also out of scope: a deleted or weaker test, and a swallowed error path. If a cleanup needs one of these, stop that cleanup. Put the question in your report, so that the caller asks the user (`dev-essentials:engineering-discipline` Rule 2). With `--autonomous`, keep the code and list the skipped cleanup in the report.
4. Build and test again. A test that the cleanup breaks is a regression of this session (Rule 1 of the same skill). For .NET, follow `dev-essentials:dotnet-build-test`.
5. Commit the cleanup as **a separate commit on top**. Stage explicit paths, never `git add -A` or `git add .`.

   ```bash
   git -C "<worktree>" commit -m "<Issue ref> — simplify: <summary of cleanups>"
   ```

   In `single` mode, it goes on top of the squashed commit. **Never `--amend` into that commit, and never squash again.** The end state is two commits. In `per-phase` mode, it goes on top of the phase and review-round commits.
6. A pass that changes nothing is valid. Make no empty commit and invent no cleanup. Report "simplify pass found nothing worth changing" and go on.

### Phase 5 — Report and stop

Return control to **Phase 4 (Report)** of RIRR. It writes the report through `dev-essentials:save-context`, as the last step of the run. The call passes no flag, so `save-context` runs in its default mode. Its cleanup keeps every file of this run, also the Phase 2 context document. Before it deletes a file of an older session, it asks the user. It prints no continuation prompt, unless the user asks for one in this run. Do not assume the default path `<--notes-dir>/Results/<slug>-report.md`. Take the path from the message in which that phase names it. Add to the report:

- The Phase 2 sweep: the items read, the pattern that they set, how the implementation followed it, each conflict and its resolution, and the path of the context document.
- The Phase 4 pass: ran or skipped, what it changed, its commit subject, and the real output of the build and tests after it.
- **The real commit topology**: `git -C "<worktree>" log --oneline <RUN_BASE_SHA>..HEAD`. In `single` mode, the expected result is **one task commit plus one simplify commit**, or only the task commit after an empty pass. If the result differs, report it and explain why. For Phase 4, `git -C "<worktree>" log --oneline <SIMPLIFY_BASE_SHA>..HEAD` must show exactly one commit, or zero after an empty pass.
- The absolute worktree path and the branch name.
- Each gate that this run or RIRR passed without a stop.

Print the report only. Step 5 of `save-context` can list files or branches that wait for the yes of the user. If it does, ask its one Step 6 question after the report. When the user says yes, delete the listed files in this session, with the safety rules of Step 5. If the user asks for a continuation prompt in this run, print it last. Else print no continuation prompt for the next session.

**Do not push.** Wait for the review of the user. Push only with `--push` in this invocation, and only after the report.
