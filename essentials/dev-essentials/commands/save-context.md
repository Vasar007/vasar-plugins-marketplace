---
description: Save session context, findings, and progress to a research file for future sessions
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

| Flag              | Description                                                      |
|-------------------|------------------------------------------------------------------|
| `--change <name>` | Pull context from an OpenSpec change (reads its artifacts)       |
| `--plan <path>`   | Pull context from a plan/task file                               |
| `--compact`       | When updating an existing file, aggressively compact old content |

## Steps

### 1. Determine output path and context source

**Auto-detection** (no explicit `--change` or `--plan`):

- Check conversation context for clues:
  - If an OpenSpec change was discussed, treat as `--change <name>`
  - If a plan file was discussed, treat as `--plan <path>`
  - Otherwise, treat as a generic session
- If a name (not a path) is given as argument, write to `Notes/Results/<name>-research.md`
- If a path is given, write to that path
- If nothing is given and nothing can be inferred, use **AskUserQuestion** to ask:
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
- Work item references (TFS IDs) if mentioned in conversation

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

### 5. Confirm to user

Show:

- Where the file was saved
- Brief summary of what was captured
- Tip: "Use `--context <path>` with `/implement` or `/opsx-implement` to load this in a future session."

## Guardrails

- Do NOT fabricate information — only capture what actually happened in the conversation
- Do NOT include raw code dumps — summarize findings, reference file paths
- Keep it concise — this is a handoff document, not a transcript
- Preserve existing content when updating — never lose prior session data
- If the conversation has very little to save, say so instead of writing a near-empty file
