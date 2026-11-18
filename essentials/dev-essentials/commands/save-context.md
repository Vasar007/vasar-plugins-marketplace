---
description: Save session context, findings, and progress to a research file for future sessions, then clean up finished context files
argument-hint: "[name-or-path] [--change <name>] [--plan <path>] [--compact] [--no-cleanup] [--continuation-prompt] [--mode interactive|partial|full]"
---

Save the current session's context, research findings, decisions, and progress to a Markdown file so future sessions can pick up where this one left off.

The notes folder is `${user_config.notes_dir}`. If that value still shows as a `${...}` placeholder, no value is saved, and the notes folder is `Notes`.

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
| `--continuation-prompt`    | Print Step 7's next-session continuation prompt (off by default)    |
| `--mode interactive\|partial\|full` | The work mode. The default is `partial`. `dev-essentials:work-modes` defines the modes, and the gate table in "Autonomy" says what each mode does here. |

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the three modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Step 1: no name for the file | Name it after the main topic, and say so | Ask | Same as partial |
| Step 5: finished files of this session | Move them to the backup with no stop | Same | Same |
| Step 5: a file of an older session, or a stale branch | List it, and act only after the yes of the user | Same | Move the file to the backup. Delete a branch only under the rule below |

In the full mode, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If both checks below pass, you can delete such a branch with `git branch -D`. First, its pull request is merged. Find the pull request with `list_pull_requests`, with `head: "<owner>:<branch>"` and `state: "all"`. `<owner>` is the `owner` value of the call. The default state lists open pull requests only, and GitHub ignores a `head` value without the `<owner>:` prefix. Then read the pull request with `pull_request_read` (`method: "get"`), and make sure that `merged` is `true`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the run cannot read the state of the pull request, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.

## Steps

### 1. Determine output path and context source

Find the context source. Without `--change` or `--plan`, look at the conversation:

- If an OpenSpec change was discussed, treat the run as `--change <name>`.
- If a plan file was discussed, treat the run as `--plan <path>`.
- Else, treat it as a generic session.

Find the output path. The value of `--change` or `--plan` names the context source. It is never the output path.

- If a name (not a path) is given, write to `Results/<name>-research.md` in the notes folder.
- If a path is given, write to that path.
- If no name or path is given, use the context source. For a change, write to `Results/<change-name>-research.md` in the notes folder. For a plan file, use its file name without `.md`: `my-plan.md` becomes `Results/my-plan-research.md` in the notes folder.
- If nothing is given and nothing can be inferred: outside the interactive mode, name the file after the main topic of the session, as a short kebab-case slug, and say so in Step 6. In the interactive mode, use **AskUserQuestion** to ask:
  > "What name do you want for this research file? (for example, `investigate-bug-123` or `refactor-auth`)"

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
   - Move to the backup (the default of this step, so it needs no new stop): finished work of this session. For example: a plan or draft whose result landed in a merged PR or a published release, and a draft replaced by a chosen version. Also a review report whose fixes landed, and a `_`-prefixed progress file whose task is done.
   - Trim: a file that open work still needs. Remove the parts that are done or no longer true. Keep the rest.
   - Keep: the saved file, the files of work that still runs, and raw history exports such as session transcripts.
   - Ask: a file from an older session, and a branch that looks stale. List each one with the reason in Step 6. Move the file to the backup only after the user says yes. In the full mode, put a file from an older session in the group "Move to the backup" and list it in Step 6. A branch follows the safety rules below.
3. Move the files of the group "Move to the backup" with the script `backup_move.py` of this plugin. The script moves each file to a backup folder outside the workspace and keeps its path relative to the workspace. It never deletes a file, so a wrong "finished" call loses nothing. First run it without `--apply`. It prints the plan and the `BACKUP` folder. Then run it with `--apply` and that folder:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/backup_move.py" --workspace "<repo root>" <file> ...
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/backup_move.py" --workspace "<repo root>" --backup "<BACKUP folder>" --apply <file> ...
   ```

   If the plan has a `REFUSE` line, the script moves no file. Keep each refused file, and list it with its reason in Step 6. Then run the script again without the refused files. The script needs Python 3 and git. On Windows, run it in the Bash tool (Git Bash).
4. In the saved file and in the trimmed files, update facts that are no longer true. Examples: an old commit SHA, an old version, or a "this session" frame from an earlier date.
5. Fix each link to a moved file. Remove the link, or point it to the file that now holds the fact.

Safety rules:

- Never delete a notes file in this step. The backup folder keeps each moved file until the user deletes it.
- Move only files that git does not track. The script refuses a tracked file. Before you trim a file, run `git ls-files -- <path>`. If it prints the path, do not change the file in this step.
- If you are not sure that the work of a file is finished, keep the file and list it in Step 6.
- Do not move a file from an older session, and do not delete a branch, without the user's yes or the full mode.
- For a stale branch, delete only the local branch, with `git branch -d`. If the remote branch still exists, list it for the user. Do not delete it. If `git branch -d` refuses the branch, list it for the user. Use `git branch -D` only after the user's yes, with a warning that commits that are not merged get lost. In the full mode, use it only after both checks of the squash-merge exception in "Autonomy" pass. If either check fails, or the pull request state cannot be read, do not delete the branch. List it for the user in Step 6. List any other refused branch for the user.

### 6. Confirm to user

Show:

- Where the file was saved
- Brief summary of what was captured
- What Step 5 did: the moved files and the path of the backup folder, the trimmed files, and the fixed links. If Step 5 did not run, say why in one line.
- The Step 5 candidates that wait for the user's yes, each with its reason, as one question

Then go to Step 7. Without a request of the user, Step 7 emits nothing.

### 7. Emit the next-session continuation prompt (opt-in)

If the user asks for this prompt, emit it. The user asks with `--continuation-prompt`, or in words in the request for this run. Without such a request, emit no prompt. A command that follows these steps as one of its own steps does not change this rule. The text of a command or a skill that asks for the prompt does not change it either. If Step 4 wrote no file because of the near-empty guardrail below, skip the prompt.

If the user asked for it, emit a short prompt for a fresh session, ready to paste, in a fenced `text` code block. The prompt is the **last thing in the response**. It comes after the output of Step 6. If another command follows these steps as one of its own steps, the prompt also comes after the final summary of that command.

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

- Do not fabricate information. Capture only what happened in the conversation.
- Do not include raw code dumps. Summarize the findings, and give the file paths.
- Keep it short. This is a handoff document, not a transcript.
- If you update an existing file, keep its content. Never lose the data of an earlier session.
- Step 5 removes only content that is finished or no longer true, and only under its safety rules
- If the conversation has very little to save, say so instead of writing a near-empty file
