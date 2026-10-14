---
description: Save session context, findings, and progress to a research file for future sessions, then clean up finished context files
argument-hint: "[name-or-path] [--change <name>] [--plan <path>] [--compact] [--no-cleanup] [--no-continuation-prompt] [--interactive] [--autonomous]"
---

Save the current session's context, research findings, decisions, and progress to a Markdown file so future sessions can pick up where this one left off.

**Arguments**: $ARGUMENTS

- Format: `[name-or-path] [options]`
- Examples:
  - *(no args)*: detect the context source and the file name from the conversation (see Step 1)
  - `add-order-discounts`: save as `Notes/Results/add-order-discounts-research.md`
  - `Notes/Results/my-investigation.md`: save to an explicit path
  - `--change add-order-discounts`: use the context of an OpenSpec change, and save as `Notes/Results/add-order-discounts-research.md`
  - `--plan Notes/Results/my-plan.md`: use the context of a plan file, and save as `Notes/Results/my-plan-research.md`

**Options:**

| Flag                       | Description                                                         |
|----------------------------|---------------------------------------------------------------------|
| `--change <name>`          | Pull context from an OpenSpec change (reads its artifacts)          |
| `--plan <path>`            | Pull context from a plan/task file                                  |
| `--compact`                | When updating an existing file, aggressively compact old content    |
| `--no-cleanup`             | Skip Step 5's light cleanup of context files (runs by default)      |
| `--no-continuation-prompt` | Skip Step 7's next-session continuation prompt (emitted by default) |
| `--interactive`            | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous`             | Do not stop at any gate. This includes the gate before deletion. The run still stops for a question that blocks the work. See "Autonomy". |

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

## Steps

### 1. Determine output path and context source

Find the context source. Without `--change` or `--plan`, look at the conversation:

- If an OpenSpec change was discussed, treat the run as `--change <name>`.
- If a plan file was discussed, treat the run as `--plan <path>`.
- Else, treat it as a generic session.

Find the output path. The value of `--change` or `--plan` names the context source. It is never the output path.

- If a name (not a path) is given, write to `Notes/Results/<name>-research.md`.
- If a path is given, write to that path.
- If no name or path is given, use the context source. For a change, write to `Notes/Results/<change-name>-research.md`. For a plan file, use its file name without `.md`: `my-plan.md` becomes `Notes/Results/my-plan-research.md`.
- If nothing is given and nothing can be inferred: without `--interactive`, name the file after the main topic of the session, as a short kebab-case slug, and say so in Step 6. With `--interactive`, use **AskUserQuestion** to ask:
  > "What should I call this research file? (e.g., `investigate-bug-123`, `refactor-auth`)"

### 2. Gather context

Collect the following from the current conversation. Skip sections that have no relevant content.

**Always gather:**

- **What was done**: the actions taken, the files read, the code written, and the investigations.
- **Key decisions**: the choices made and the reason for each. For three or more, use a table.
- **Issues found**: the problems, bugs, and inconsistencies found.
- **What's next**: the remaining work, the open questions, and the suggested next steps.

**If `--change <name>`** (OpenSpec context), also gather:

- Change name, branch, date
- Link to openspec change directory
- Which artifacts exist and their status (`openspec status --change "<name>"`)
- The GitHub issue and Projects references that the conversation mentions (`#123`, a project item, or a URL)

**If `--plan <path>`** (plan context), also gather:

- Plan file path and current progress (N/M tasks complete)
- Which phases/sections were worked on

**Also gather, where the session has them:**

- **Key file paths**: the important files that were read, changed, or named for future work. Group them by category: core, tests, configuration, docs.
- **Codebase patterns**: the patterns or conventions found that a future session needs to know.

### 3. Check for existing file

If the output file already exists:

- Read the existing content
- **Merge** new findings into the existing structure:
  - Update "What Was Done": append the new work. For more than one session, use a sub-section with a date for each session.
  - Update "Key Decisions": add the new rows to the table.
  - Update "Issues Found": add the new issues, and mark the resolved ones.
  - Update "What's Next": replace it with the current state.
  - Update "Key File Paths": merge the new paths.
- If `--compact` is specified, summarize older session content into a brief paragraph before adding new content

### 4. Write the file

Use this structure (skip empty sections):

```markdown
# <Title> — Research

## Overview

<Brief 1-2 sentence description of what this research covers>
<Change/plan reference if applicable>
Branch: `<current branch>`
Date: <today>

## What Was Done

<Organized summary of work performed>

## Key Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | ...      | ...       |

## Issues Found

- **<Issue>** — <description and impact>

## Key File Paths

### <Category>

- `path/to/file.cs` — <brief role>

## What's Next

1. <Next step>
2. <Next step>
```

Make sure that the file follows the Markdown conventions: an H1 title, blank lines around headings, and no bare URLs.

### 5. Light cleanup of context files

Unless `--no-cleanup` was passed, clean up the context and handoff files of this session. Skip this step in two cases. The first case: Step 4 wrote no file (the near-empty guardrail). The second case: another command follows these steps as one of its own steps, because that command still uses its plan and progress files. A calling command can ask for the cleanup in words.

This is a light pass, not a full trim. To trim one file in depth, use `dev-essentials:trim-artifacts`.

1. List the files in the notes folder that holds the saved file (for example `Notes/`), with their dates. Find the links to them in the saved file and in the other notes files. If the project has agent memory files, find the links there too.
2. Put each file into one group:
   - Delete (the default of this step, so it needs no new stop): finished work of this session. For example: a plan or draft whose result landed in a merged PR or a published release, and a draft replaced by a chosen version. Also a review report whose fixes landed, and a `_`-prefixed progress file whose task is done.
   - Trim: a file that open work still needs. Remove the parts that are done or no longer true. Keep the rest.
   - Keep: the saved file, the files of work that still runs, and raw history exports such as session transcripts.
   - Ask: a file from an older session, and a branch that looks stale. List each one with the reason in Step 6. Delete it only after the user says yes. With `--autonomous`, put a file from an older session in the group "Delete" and list it in Step 6. A branch follows the safety rules below.
3. In the saved file and in the trimmed files, update facts that are no longer true. Examples: an old commit SHA, an old version, or a "this session" frame from an earlier date.
4. Fix each link to a deleted file. Remove the link, or point it to the file that now holds the fact.

Safety rules:

- Delete only files that git does not track. Before you delete or trim a file, run `git ls-files -- <path>`. If it prints the path, do not change the file in this step.
- If you are not sure that the work of a file is finished, keep the file and list it in Step 6.
- Do not delete a file from an older session or a branch without the user's yes or `--autonomous`.
- For a stale branch, delete only the local branch, with `git branch -d`. If the remote branch still exists, list it for the user. Do not delete it. If `git branch -d` refuses the branch, list it for the user. Use `git branch -D` only after the user's yes, with a warning that commits that are not merged get lost. With `--autonomous`, use it only after both checks pass. A squash merge makes `git branch -d` refuse such a branch. First, the pull request of the branch is merged. Find it with `list_pull_requests`, with `head: "<owner>:<branch>"` and `state: "all"`. `<owner>` is the `owner` value of the call. The default state lists open pull requests only, and GitHub ignores a `head` value without the `<owner>:` prefix. Then read it with `pull_request_read` (`method: "get"`), and make sure that `merged` is `true`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the pull request state cannot be read, do not delete the branch. List it for the user in Step 6. List any other refused branch for the user.

### 6. Confirm to user

Show:

- Where the file was saved
- Brief summary of what was captured
- What Step 5 did: the deleted files, the trimmed files, and the fixed links. If Step 5 did not run, say why in one line.
- The Step 5 candidates that wait for the user's yes, each with its reason, as one question

Then continue to Step 7 to emit the next-session continuation prompt.

### 7. Emit the next-session continuation prompt

Emit a short prompt for a fresh session, ready to paste, in a fenced `text` code block. Skip it in two cases: `--no-continuation-prompt` was passed, or Step 4 wrote no file because of the near-empty guardrail below. The prompt is the **last thing in the response**. It comes after the output of Step 6. If another command follows these steps as one of its own steps, the prompt also comes after the final summary of that command.

Template. The third line is a *location* line. Rule **(a)** gives its form. If this session ran in the repo root on the default branch, omit the line.

```text
Restore context from `<path to the saved context file>` — read it in full,
including anything it points at that you need.
Worktree: `<absolute worktree path>`, branch `<branch name>`.
Then stop and wait for my instructions. Do not start any work, do not re-plan,
and do not summarize the file back to me.
```

Rules for the prompt:

- **(a)** Name the path of the saved file. If the file is in the repo, give the path relative to the repo root. Then add a location line, so that the next session starts in the right copy and on the right branch, not in the repo root. Decide its two facts separately. If this session was not on the default branch, include the **branch name**. If this session ran in a worktree, include the **absolute path of the worktree**. Else, leave the path out. Use the label of the case that is true:
  - A worktree and a branch that is not the default: ``Worktree: `<absolute worktree path>`, branch `<branch name>`.``
  - A branch that is not the default, and no worktree: ``Branch: `<branch name>`.``
  - A worktree on the default branch: ``Worktree: `<absolute worktree path>`.``
  - Neither: omit the line.
- **(b)** Always say "stop and wait for my instructions" explicitly.
- **(c)** Forbid the two failure modes in words: to start work, and to restate or summarize the content of the file. A prompt that only says "restore context and wait" makes the next session summarize the file and propose a plan.
- **(d)** The prompt holds only the lines of the template: the restore instruction with the path, the location line, the wait instruction, and the prohibitions. It has **no** findings, decisions, task lists, next steps, plans, or commands to run. The file holds these, or the user decides them.
- **(e)** Hard cap: **6 lines**. If there is more to say, put it in the file, not in the prompt.

## Guardrails

- Do NOT fabricate information. Capture only what happened in the conversation.
- Do NOT include raw code dumps. Summarize the findings, and give the file paths.
- Keep it short. This is a handoff document, not a transcript.
- If you update an existing file, keep its content. Never lose the data of an earlier session.
- Step 5 removes only content that is finished or no longer true, and only under its safety rules
- If the conversation has very little to save, say so instead of writing a near-empty file
