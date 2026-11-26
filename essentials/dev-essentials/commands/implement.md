---
description: Implement tasks from a plan file (no spec-framework dependency)
---

Implement tasks from a plan or task list file.

The notes folder is the folder that `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md` gives. Read that file before the first read or write in the notes folder.

**Arguments**: $ARGUMENTS

- Format: `<path-to-plan-file> [phase/section numbers] [options]`
- Examples:
  - `plans/my-plan.md`: implement all tasks
  - `plans/my-plan.md 3`: implement only section/phase 3
  - `plans/my-plan.md 2-5`: implement sections 2 through 5
  - `plans/my-plan.md 1,3,7`: implement sections 1, 3, and 7
  - `plans/my-plan.md 3-5 --commit`: implement and commit after each phase
  - `plans/my-plan.md --commit-push`: commit and push after each phase
  - `plans/my-plan.md --context plans/research.md`: use a specific context file
- If no arguments, use the **AskUserQuestion tool** to ask for the plan file path.

**Options:**

| Flag               | Default | Description                                              |
|--------------------|---------|----------------------------------------------------------|
| `--commit`         | off     | Commit changes after each completed phase/section        |
| `--commit-push`    | off     | Commit and push to remote after each completed phase     |
| `--context <path>` | auto    | Path to a research/context file with prior session notes |
| `--mode interactive\|partial\|full` | `partial` | The work mode. `dev-essentials:work-modes` defines the modes, and the gate table in "Autonomy" says what each mode does here. |

If neither `--commit` nor `--commit-push` is specified, changes are left uncommitted (working tree only).

## Autonomy

Before the first step, load `dev-essentials:work-modes` with the `Skill` tool. It defines the option `--mode`, the modes, the rules for every mode, and the hard stops. This table lists each gate of this workflow and what each mode does there.

| Gate | Partial (the default) | Interactive | Full |
| --- | --- | --- | --- |
| Step 3: the task list | Show it and continue | Wait for approval | Same as partial |
| Step 4 and Guardrails: a critical decision | Ask | Ask | Decide, and list it |
| Guardrails: a plan issue with a clear fix | Update the plan, and list the change | Pause, and suggest updates | Same as partial |
| Step 5: push | Only with `--commit-push`, which approves it | Same | Same |
| Step 6: `/save-context` cleanup | Its own gates, with the mode of this run | Same | Same |

## Steps

1. **Load the plan**

   Read the specified plan file. Parse it to identify:
   - Sections/phases (headers like `## Phase 1`, `## 1. Category`, numbered sections)
   - Individual tasks (checkbox items `- [ ]`, numbered items, bullet points)
   - Any context or notes provided in the plan

2. **Load context**

   Check for prior context in this order:
   1. If `--context <path>` was specified, read that file.
   2. Otherwise, derive a research file name from the plan file (for example, `my-plan.md` → `Results/my-plan-research.md` in the notes folder). If it exists, read it.
   3. As the last fallback, run the command of item 3 of `${CLAUDE_PLUGIN_ROOT}/references/notes-root.md`. It finds a KB clone. If it prints a folder, read `_claude/RULES.md` in that folder. Then read each rules index that it loads, and the index that it names for the project of this repository. If it prints nothing, skip this item.

3. **Determine which tasks to implement**

   - If section/phase numbers are specified, filter to only those.
   - If no filter, implement all incomplete tasks.
   - Show the user which tasks will be implemented. Outside the interactive mode, continue. In the interactive mode, ask the user to approve the list first.

4. **Implement tasks**

   For each pending task:
   - Announce which task is being worked on.
   - **Follow existing patterns** in the codebase. Read the related files before you write new code.
   - **If unclear about something, ask the user**. Do not improvise. In the full mode, decide as `dev-essentials:work-modes` says.
   - Use the skills that fit the change type and the stack, for example `dotnet-backend-dev:create-domain-model` and `dotnet-backend-dev:create-tests` in a .NET repo with that plugin.
   - Mark each task complete in the plan file as you finish it: `- [ ]` → `- [x]`

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase/section:
   - Stage the files relevant to that phase by explicit path. Never use `git add -A` or `git add .`. Do not stage the plan file or the research file of Step 6. They are working files of this run.
   - Write the commit message in the commit style of the repo. If the `CLAUDE.md` of the repo has commit rules, follow them. Else copy the style of `git log --oneline -20`. Describe the change to the code. Do not put plan numbers such as `Phase 2` or `Task 3.1`, or the path of the plan file, in the message. A later reader of the history does not have the plan (`dev-essentials:engineering-discipline` Rule 3).
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do not push unless `--commit-push` was explicitly specified.

6. **Save research and findings**

   Run this step after the selected sections. If the run stops early, run it before the stop. Follow the `/save-context` command logic with `--plan "<path>"`, plus the `--mode` of this run.
   - If `--context <path>` was given, save to that path. Else save to the research file name of Step 2 (for example, `Results/my-plan-research.md` in the notes folder).
   - Include: what was done, decisions made, issues found, what's next.
   - If the user asks for a continuation prompt in this run, print it after the summary of Step 7. Else print no continuation prompt for the next session.

7. **Output results**

   Summarize to the user:
   - Tasks completed this session
   - Overall progress
   - Any issues or blockers
   - Key decisions made
   - What to do next

## Guardrails

- **Do not improvise**. If you are not sure, ask the user for clarification. In the full mode, decide as `dev-essentials:work-modes` says.
- Stop after the specified sections. Do not continue into sections that the user did not select.
- Always save research findings before stopping
- If implementation reveals plan issues: outside the interactive mode, update the plan for a clear fix, and list the change in the output. If the fix needs a critical decision, follow "Autonomy". In the interactive mode, pause and suggest updates.
- The plan file is the single source of truth. Keep it up to date.
