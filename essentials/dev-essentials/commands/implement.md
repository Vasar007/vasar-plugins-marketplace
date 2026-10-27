---
description: Implement tasks from a plan file (no spec-framework dependency)
---

Implement tasks from a plan or task list file.

**Arguments**: $ARGUMENTS

- Format: `<path-to-plan-file> [phase/section numbers] [options]`
- Examples:
  - `Notes/Results/my-plan.md`: implement all tasks
  - `Notes/Results/my-plan.md 3`: implement only section/phase 3
  - `Notes/Results/my-plan.md 2-5`: implement sections 2 through 5
  - `Notes/Results/my-plan.md 1,3,7`: implement sections 1, 3, and 7
  - `Notes/Results/my-plan.md 3-5 --commit`: implement and commit after each phase
  - `Notes/Results/my-plan.md --commit-push`: commit and push after each phase
  - `Notes/Results/my-plan.md --context Notes/Results/research.md`: use a specific context file
- If no arguments, use the **AskUserQuestion tool** to ask for the plan file path.

**Options:**

| Flag               | Default | Description                                              |
|--------------------|---------|----------------------------------------------------------|
| `--commit`         | off     | Commit changes after each completed phase/section        |
| `--commit-push`    | off     | Commit and push to remote after each completed phase     |
| `--context <path>` | auto    | Path to a research/context file with prior session notes |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

If neither `--commit` nor `--commit-push` is specified, changes are left uncommitted (working tree only).

## Autonomy

This workflow has three modes. The user picks one with a flag: the default (no flag), `--interactive`, or `--autonomous`. A gate is a step where the run can stop and ask the user. This table lists each gate of this workflow and what each mode does there.

| Gate | Default | `--interactive` | `--autonomous` |
| --- | --- | --- | --- |
| Step 3: the task list | Show it and continue | Wait for approval | Same |
| Step 4 and Guardrails: a critical decision | Ask | Ask | Decide, and list it |
| Guardrails: a plan issue with a clear fix | Update the plan, and list the change | Pause, and suggest updates | Same |
| Step 5: push | Only with `--commit-push`, which approves it | Same | Same |
| Step 6: `/save-context` cleanup | Its own gates, with the flag of this run | Same | Same |

These rules apply in every mode:

- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that the run cannot fix also stops the run. Do not ask in other cases.
- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default of the gate, and continue.
- The final report lists each gate that the run passed without a stop. With `--autonomous`, it also lists each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It adds no steps. A step that runs only with a flag such as `--push` still needs that flag, and the flag is the approval of that step.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Steps

1. **Load the plan**

   Read the specified plan file. Parse it to identify:
   - Sections/phases (headers like `## Phase 1`, `## 1. Category`, numbered sections)
   - Individual tasks (checkbox items `- [ ]`, numbered items, bullet points)
   - Any context or notes provided in the plan

2. **Load context**

   Check for prior context in this order:
   1. If `--context <path>` was specified, read that file.
   2. Otherwise, derive a research file name from the plan file (for example, `my-plan.md` → `Notes/Results/my-plan-research.md`). If it exists, read it.
   3. As a final fallback, check the auto-memory directory (`MEMORY.md` and topic files) for relevant project notes.

3. **Determine which tasks to implement**

   - If section/phase numbers are specified, filter to only those.
   - If no filter, implement all incomplete tasks.
   - Show the user which tasks will be implemented. Without `--interactive`, continue. With `--interactive`, ask the user to approve the list first.

4. **Implement tasks**

   For each pending task:
   - Announce which task is being worked on.
   - **Follow existing patterns** in the codebase. Read the related files before you write new code.
   - **If unclear about something, ask the user**. Do not improvise. With `--autonomous`, decide as "Autonomy" says.
   - Use the skills that fit the change type and the stack, for example `dotnet-backend-dev:create-domain-model` and `dotnet-backend-dev:create-tests` in a .NET repo with that plugin.
   - Mark each task complete in the plan file as you finish it: `- [ ]` → `- [x]`

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase/section:
   - Stage the files relevant to that phase by explicit path. Never use `git add -A` or `git add .`. Do not stage the plan file or the research file of Step 6. They are working files of this run.
   - Write the commit message in the commit style of the repo. If the `CLAUDE.md` of the repo has commit rules, follow them. Else copy the style of `git log --oneline -20`. Describe the change to the code. Do not put plan numbers such as `Phase 2` or `Task 3.1`, or the path of the plan file, in the message. A later reader of the history does not have the plan (`dev-essentials:engineering-discipline` Rule 3).
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do not push unless `--commit-push` was explicitly specified.

6. **Save research and findings**

   Run this step after the selected sections. If the run stops early, run it before the stop. Follow the `/save-context` command logic with `--plan "<path>"`, plus `--interactive` or `--autonomous` for a run that has it.
   - If `--context <path>` was given, save to that path. Else save to the research file name of Step 2 (for example, `Notes/Results/my-plan-research.md`).
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

- **Do not improvise**. If you are not sure, ask the user for clarification. With `--autonomous`, decide as "Autonomy" says.
- Stop after the specified sections. Do not continue into sections that the user did not select.
- Always save research findings before stopping
- If implementation reveals plan issues: without `--interactive`, update the plan for a clear fix, and list the change in the output. If the fix needs a critical decision, follow "Autonomy". With `--interactive`, pause and suggest updates.
- The plan file is the single source of truth. Keep it up to date.
