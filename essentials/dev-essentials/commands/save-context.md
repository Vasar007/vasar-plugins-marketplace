---
description: Save session context, findings, and progress to a research file for future sessions, then clean up finished context files
argument-hint: "[name-or-path] [--change <name>] [--plan <path>] [--compact] [--no-cleanup] [--no-continuation-prompt] [--interactive]"
---

Save the current session's context, research findings, decisions, and progress to a Markdown file so future sessions can pick up where this one left off.

**Arguments**: $ARGUMENTS

- Format: `[name-or-path] [options]`
- Examples:
  - *(no args)* — auto-detect from conversation context (openspec change, plan file, or ask)
  - `enhance-provisioning-plans` — save as `Notes/Results/enhance-provisioning-plans-research.md`
  - `Notes/Results/my-investigation.md` — save to an explicit path
  - `--change enhance-provisioning-plans` — explicitly use openspec change context
  - `--plan Notes/Results/my-plan.md` — explicitly use plan file context

**Options:**

| Flag                       | Description                                                         |
|----------------------------|---------------------------------------------------------------------|
| `--change <name>`          | Pull context from an OpenSpec change (reads its artifacts)          |
| `--plan <path>`            | Pull context from a plan/task file                                  |
| `--compact`                | When updating an existing file, aggressively compact old content    |
| `--no-cleanup`             | Skip Step 5's light cleanup of context files (runs by default)      |
| `--no-continuation-prompt` | Skip Step 7's next-session continuation prompt (emitted by default) |
| `--interactive` | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |

## Autonomy

By default, this workflow does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. This default approval covers the whole task, up to the merge.

- At a decision gate, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run approved without a stop.
- These stops stay in every mode: deletion of data, posts to outside systems (for example GitHub comments, reviews, and issues, or documentation pages), push, and pull request creation. The merge always stays with the user.
- An action that the user approved for this run needs no new stop. Two cases count as approval. The first is a flag such as `--push`, `--commit-push`, `auto-push`, or `autonomous`. The second is a step of this workflow that names the action as its default.
- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Ask the user about every other critical decision.
- If a rule says to ask before a Fable dispatch that neither the user nor the defaults of this workflow chose, do not ask. Use Opus, and name the step in the final report.
- With `--interactive`, every gate stops and waits for the user, as the gate text says.
- When this workflow runs another workflow and this run has `--interactive`, pass the flag on.

## Steps

### 1. Determine output path and context source

**Auto-detection** (no explicit `--change` or `--plan`):

- Check conversation context for clues:
  - If an OpenSpec change was discussed, treat as `--change <name>`
  - If a plan file was discussed, treat as `--plan <path>`
  - Otherwise, treat as a generic session
- If a name (not a path) is given as argument, write to `Notes/Results/<name>-research.md`
- If a path is given, write to that path
- If nothing is given and nothing can be inferred: without `--interactive`, name the file after the main topic of the session, as a short kebab-case slug, and say so in the confirmation step. With `--interactive`, use **AskUserQuestion** to ask:
  > "What should I call this research file? (e.g., `investigate-bug-123`, `refactor-auth`)"

### 2. Gather context

Collect the following from the current conversation. Skip sections that have no relevant content.

**Always gather:**

- **What was done** — summarize actions taken, files read, code written, investigations performed
- **Key decisions** — choices made and their rationale (table format if 3+)
- **Issues found** — problems, bugs, inconsistencies discovered
- **What's next** — remaining work, open questions, suggested next steps

**If `--change <name>`** (OpenSpec context), also gather:

- Change name, branch, date
- Link to openspec change directory
- Which artifacts exist and their status (`openspec status --change "<name>"`)
- GitHub issue and Projects references (`#123`, a project item, or a URL) if mentioned in conversation

**If `--plan <path>`** (plan context), also gather:

- Plan file path and current progress (N/M tasks complete)
- Which phases/sections were worked on

**Always gather if relevant:**

- **Key file paths** — important files that were read, modified, or identified for future work (group by category: core, tests, config, docs)
- **Codebase patterns** — notable patterns or conventions discovered that future sessions should know

### 3. Check for existing file

If the output file already exists:

- Read the existing content
- **Merge** new findings into the existing structure:
  - Update "What Was Done" — append new work (use sub-sections with dates if multiple sessions)
  - Update "Key Decisions" — add new rows to the table
  - Update "Issues Found" — add new issues, mark resolved ones
  - Update "What's Next" — replace with current state
  - Update "Key File Paths" — merge new paths
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

Ensure the file follows markdown conventions (H1 title, blank lines around headings, no bare URLs).

### 5. Light cleanup of context files

Unless `--no-cleanup` was passed, clean up the context and handoff files of this session. Skip this step in two cases. The first case: Step 4 wrote no file (the near-empty guardrail). The second case: another command follows these steps as one of its own steps, because that command still uses its plan and progress files. A calling command can ask for the cleanup in words.

This is a light pass, not a full trim. To trim one file in depth, use `dev-essentials:trim-artifacts`.

1. List the files in the notes folder that holds the saved file (for example `Notes/`), with their dates. Find the links to them in the saved file and in the other notes files. If the project has agent memory files, find the links there too.
2. Put each file into one group:
   - Delete (the default of this step, so it needs no new stop): finished work of this session. For example: a plan or draft whose result landed in a merged PR or a published release, and a draft replaced by a chosen version. Also a review report whose fixes landed, and a `_`-prefixed progress file whose task is done.
   - Trim: a file that open work still needs. Remove the parts that are done or no longer true. Keep the rest.
   - Keep: the saved file, the files of work that still runs, and raw history exports such as session transcripts.
   - Ask: a file from an older session, and a branch that looks stale. List each one with the reason in Step 6. Delete it only after the user says yes.
3. In the saved file and in the trimmed files, update facts that are no longer true. Examples: an old commit SHA, an old version, or a "this session" frame from an earlier date.
4. Fix each link to a deleted file. Remove the link, or point it to the file that now holds the fact.

Safety rules:

- Delete only files that git does not track. Before you delete or trim a file, run `git ls-files -- <path>`. If it prints the path, do not change the file in this step.
- If you are not sure that the work of a file is finished, keep the file and list it in Step 6.
- Do not delete a file from an older session or a branch without the user's yes.
- For a stale branch, delete only the local branch, with `git branch -d`. If the remote branch still exists, list it for the user. Do not delete it. If `git branch -d` refuses the branch, list it for the user. Use `git branch -D` only after the user's yes, with a warning that commits that are not merged get lost.

### 6. Confirm to user

Show:

- Where the file was saved
- Brief summary of what was captured
- What Step 5 did: the deleted files, the trimmed files, and the fixed links. If Step 5 did not run, say why in one line.
- The Step 5 candidates that wait for the user's yes, each with its reason, as one question

Then continue to Step 7 to emit the next-session continuation prompt.

### 7. Emit the next-session continuation prompt

Unless `--no-continuation-prompt` was passed, or the near-empty-conversation guardrail below applies (too little to save, so no file was written), emit a short, paste-ready prompt for a fresh session in a fenced `text` code block. It is the **last thing in the response** — after Step 6's confirmation, and after the calling command's own final summary when save-context is being followed as a step of a larger command.

Template (the third line is a *location* line whose form depends on what was actually in play — see rule **(a)**; omit it entirely when this session ran in the repo root on the default branch):

```text
Restore context from `<path to the saved context file>` — read it in full,
including anything it points at that you need.
Worktree: `<absolute worktree path>`, branch `<branch name>`.
Then stop and wait for my instructions. Do not start any work, do not re-plan,
and do not summarize the file back to me.
```

Rules that make this reliable:

- **(a)** Name the saved file's path — repo-relative when the file lives in the repo. Then add a location line so the next session starts in the right copy and on the right branch instead of the repo root. Decide its two facts independently: include the **branch name** whenever this session was not on the default branch, and include the **worktree's absolute path** only when this session actually ran in a worktree. Label it for the case that is true — both: ``Worktree: `<absolute worktree path>`, branch `<branch name>`.``; non-default branch, no worktree: ``Branch: `<branch name>`.``; worktree on the default branch: ``Worktree: `<absolute worktree path>`.``; neither: omit the line entirely.
- **(b)** Always say "stop and wait for my instructions" explicitly.
- **(c)** Explicitly forbid the two failure modes: starting work, and restating/summarizing the file's content. Stating the prohibition is what makes the prompt reliable — "restore context and wait" alone reliably produces a next session that immediately summarizes the file and proposes a plan.
- **(d)** Contains **no** findings, decisions, task lists, or next steps of its own. Those are the file's job, not the prompt's.
- **(e)** Hard cap: **6 lines**. Do not let this grow into a mini-briefing over time — if there is more to say, it belongs in the file, not the prompt.

## Guardrails

- Do NOT fabricate information — only capture what actually happened in the conversation
- Do NOT include raw code dumps — summarize findings, reference file paths
- Keep it concise — this is a handoff document, not a transcript
- Preserve existing content when updating — never lose prior session data
- Step 5 removes only content that is finished or no longer true, and only under its safety rules
- If the conversation has very little to save, say so instead of writing a near-empty file
- The Step 7 continuation prompt must not restate, summarize, or duplicate any of the file's content — path + "wait" + prohibitions only
- The Step 7 continuation prompt must not invent next steps, propose a plan, or name a command to run — that is the file's / the user's call
