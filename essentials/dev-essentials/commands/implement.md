---
description: Implement tasks from a plan file (no OpenSpec dependency)
---

Implement tasks from a plan or task list file.

**Arguments**: $ARGUMENTS

- Format: `<path-to-plan-file> [phase/section numbers] [options]`
- Examples:
  - `Notes/Results/my-plan.md` — implement all tasks
  - `Notes/Results/my-plan.md 3` — implement only section/phase 3
  - `Notes/Results/my-plan.md 2-5` — implement sections 2 through 5
  - `Notes/Results/my-plan.md 1,3,7` — implement sections 1, 3, and 7
  - `Notes/Results/my-plan.md 3-5 --commit` — implement and commit after each phase
  - `Notes/Results/my-plan.md --commit-push` — commit and push after each phase
  - `Notes/Results/my-plan.md --context Notes/Results/research.md` — use a specific context file
- If no arguments, use the **AskUserQuestion tool** to ask for the plan file path.

**Options:**

| Flag               | Default | Description                                              |
|--------------------|---------|----------------------------------------------------------|
| `--commit`         | off     | Commit changes after each completed phase/section        |
| `--commit-push`    | off     | Commit and push to remote after each completed phase     |
| `--context <path>` | auto    | Path to a research/context file with prior session notes |

If neither `--commit` nor `--commit-push` is specified, changes are left uncommitted (working tree only).

## Steps

1. **Load the plan**

   Read the specified plan file. Parse it to identify:
   - Sections/phases (headers like `## Phase 1`, `## 1. Category`, numbered sections)
   - Individual tasks (checkbox items `- [ ]`, numbered items, bullet points)
   - Any context or notes provided in the plan

2. **Load context**

   Check for prior context in this order:
   1. If `--context <path>` was specified, read that file.
   2. Otherwise, derive a research file name from the plan file (e.g., `my-plan.md` → `Notes/Results/my-plan-research.md`). If it exists, read it.
   3. As a final fallback, check the auto-memory directory (`MEMORY.md` and topic files) for relevant project notes.

3. **Determine which tasks to implement**

   - If section/phase numbers are specified, filter to only those.
   - If no filter, implement all incomplete tasks.
   - Show the user which tasks will be implemented and ask for confirmation.

4. **Implement tasks**

   For each pending task:
   - Announce which task is being worked on.
   - **Follow existing patterns** in the codebase — read related files before writing new code.
   - **If unclear about something, ask the user** — do NOT improvise.
   - Use skills from `.claude/` folder for appropriate actions (e.g., `create-domain-model`, `create-tests`, etc.).
   - Mark each task complete in the plan file as you finish it: `- [ ]` → `- [x]`

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase/section:
   - Stage all changed files relevant to the phase (use `git add` with specific file paths).
   - Commit with message format: `Phase N: Task X.Y - brief description (5-10 words)`
     - If the plan has no phases, use: `Task X - brief description`
     - If no task numbering either, use: `brief description of changes`
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do NOT push unless `--commit-push` was explicitly specified.

6. **Save research and findings**

   After completing the selected sections (or if stopping), save session context by following the `/save-context` command logic with `--plan "<path>"`.
   - If `--context <path>` was specified, save to that path; otherwise fallback to derived name (e.g., `my-plan.md` -> `Notes/Results/my-plan-research.md`)
   - Include: what was done, decisions made, issues found, what's next.
   - This includes `save-context`'s next-session continuation prompt, emitted after Step 7's summary below.

7. **Output results**

   Summarize to the user:
   - Tasks completed this session
   - Overall progress
   - Any issues or blockers
   - Key decisions made
   - What to do next

## Guardrails

- **Do NOT improvise** when uncertain — ask the user for clarification
- Follow existing codebase patterns — read before writing
- Stop after the specified sections — don't continue into unselected ones
- Always save research findings before stopping
- If implementation reveals plan issues, pause and suggest updates
- The plan file is the single source of truth — keep it updated
