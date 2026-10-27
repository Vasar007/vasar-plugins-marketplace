---
description: Implement specific phases from an OpenSpec change with research tracking
---

Implement tasks from an OpenSpec change, optionally limited to specific phases.

**Arguments**: $ARGUMENTS

- Format: `<change-name> [phase numbers] [options]`
- Examples:
  - `split-account-balancing-options`: implement all phases
  - `split-account-balancing-options 10`: implement only phase 10
  - `split-account-balancing-options 3-5`: implement phases 3 through 5
  - `split-account-balancing-options 2,4,7`: implement phases 2, 4, and 7
  - `split-account-balancing-options 3-5 --commit`: implement and commit after each phase
  - `split-account-balancing-options --commit-push`: commit and push after each phase
  - `split-account-balancing-options --context Notes/Results/research.md`: use a specific context file
- If no change name is given, run `openspec list --json`, and use the **AskUserQuestion tool** to ask which change to implement.

**Options:**

| Flag               | Default | Description                                              |
|--------------------|---------|----------------------------------------------------------|
| `--commit`         | off     | Commit changes after each completed phase                |
| `--commit-push`    | off     | Commit and push to remote after each completed phase     |
| `--context <path>` | auto    | Path to a research/context file with prior session notes |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

If neither `--commit` nor `--commit-push` is specified, changes are left uncommitted (working tree only).

## Autonomy

This workflow has three modes. The user picks one with a flag: the default (no flag), `--interactive`, or `--autonomous`. A gate is a step where the run can stop and ask the user. This table lists each gate of this workflow and what each mode does there.

| Gate | Default | `--interactive` | `--autonomous` |
| --- | --- | --- | --- |
| Step 3: the task list | Show it and continue | Show it and continue | Show it and continue |
| Step 4 and Guardrails: a critical decision | Ask | Ask | Decide, and list it |
| Guardrails: a plan issue with a clear fix | Update the artifacts, and list the change | Pause, and suggest updates | Same |
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

1. **Parse arguments**

   Extract the change name and the optional phase filter from the arguments. If no change name is given, ask as "Arguments" says.

2. **Load context**

   Check for prior context in this order:
   1. If `--context <path>` was specified, read that file.
   2. Otherwise, check for an existing research file at `Notes/Results/<change-name>-research.md`. If it exists, read it for prior context and findings.
   3. As a final fallback, check the auto-memory directory (`MEMORY.md` and topic files) for relevant project notes.

   Then load the OpenSpec artifacts:
   - Run `openspec instructions apply --change "<name>" --json` to get context files.
   - Read all context files (proposal, specs, design, tasks).

3. **Determine which tasks to implement**

   - Parse `tasks.md` to find all phases and tasks.
   - If phase numbers are specified, filter to only those phases.
   - If no phase filter, implement all incomplete tasks.
   - Show the user which tasks will be implemented.

4. **Implement tasks**

   For each pending task in the selected phases:
   - Announce which task is being worked on.
   - **Follow existing patterns** in the codebase. Read the related files before you write new code.
   - **If unclear about something, ask the user**. Do NOT improvise. With `--autonomous`, decide as "Autonomy" says.
   - Use the skills that fit the change type and the stack, for example `dotnet-backend-dev:create-domain-model` and `dotnet-backend-dev:create-tests` in a .NET repo with that plugin.
   - Mark each task complete in `tasks.md` as you finish it: `- [ ]` → `- [x]`
   - Keep the OpenSpec artifacts in sync with the code. If you find an inconsistency or an issue, update the artifacts that it affects (specs, design, tasks).
   - After this change is approved and its behavior is implemented, the living spec under `openspec/specs/` is the canonical spec. Update it there, in place. Do not back-fill finished work into `openspec/changes/<name>/`. That folder is a staging area for work that is not merged into the living spec yet. It is not a permanent record. This rule is a convention of the team. The OpenSpec tooling does not enforce it.

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase:
   - Stage the files relevant to that phase by explicit path. Never use `git add -A` or `git add .`. Do not stage the research file under `Notes/Results/`. It is a working file of this run.
   - Write the commit message in the commit style of the repo. If the `CLAUDE.md` of the repo has commit rules, follow them. Else copy the style of `git log --oneline -20`. Describe the change to the code. Do not put the phase or task numbers of `tasks.md`, such as `Phase 2` or `Task 3.1`, in the message. A later reader of the history does not have them (`dev-essentials:engineering-discipline` Rule 3).
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do NOT push unless `--commit-push` was explicitly specified.

6. **Save research and findings**

   Run this step after the selected phases. If the run stops because of a blocker, run it before the stop. Follow the `/save-context` command logic with `--change "<name>"`, plus `--interactive` or `--autonomous` for a run that has it.
   - If `--context <path>` was given, save to that path. Else save to `Notes/Results/<change-name>-research.md`.
   - Include: what was done, decisions made, issues found, what's next.
   - If the user asks for a continuation prompt in this run, print it after the summary of Step 7. Else print no continuation prompt for the next session.

7. **Output results**

   Summarize to the user:
   - Tasks completed this session
   - Overall progress (N/M tasks)
   - Any issues or blockers encountered
   - Key decisions made
   - What to do next

## Guardrails

- **Do NOT improvise**. If you are not sure, ask the user for clarification. With `--autonomous`, decide as "Autonomy" says.
- Stop after the specified phases. Do not continue into phases that the user did not select.
- Always save research findings before stopping
- If implementation reveals design issues: without `--interactive`, update the artifacts for a clear fix, and list the change in the output. If the fix needs a critical decision, follow "Autonomy". With `--interactive`, pause and suggest artifact updates.
