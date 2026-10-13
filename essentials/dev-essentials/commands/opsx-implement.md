---
description: Implement specific phases from an OpenSpec change with research tracking
---

Implement tasks from an OpenSpec change, optionally limited to specific phases.

**Arguments**: $ARGUMENTS

- Format: `<change-name> [phase numbers] [options]`
- Examples:
  - `split-account-balancing-options` — implement all phases
  - `split-account-balancing-options 10` — implement only phase 10
  - `split-account-balancing-options 3-5` — implement phases 3 through 5
  - `split-account-balancing-options 2,4,7` — implement phases 2, 4, and 7
  - `split-account-balancing-options 3-5 --commit` — implement and commit after each phase
  - `split-account-balancing-options --commit-push` — commit and push after each phase
  - `split-account-balancing-options --context Notes/Results/research.md` — use a specific context file
- If no change name provided, prompt for selection using `openspec list --json`

**Options:**

| Flag               | Default | Description                                              |
|--------------------|---------|----------------------------------------------------------|
| `--commit`         | off     | Commit changes after each completed phase                |
| `--commit-push`    | off     | Commit and push to remote after each completed phase     |
| `--context <path>` | auto    | Path to a research/context file with prior session notes |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |

If neither `--commit` nor `--commit-push` is specified, changes are left uncommitted (working tree only).

## Autonomy

By default, this workflow does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. This default approval covers the whole task, up to the merge.

- At a decision gate, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run approved without a stop.
- These stops stay in every mode: deletion of data, posts to outside systems (for example GitHub comments, reviews, and issues, or documentation pages), push, and pull request creation. The merge always stays with the user.
- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Ask the user about every other critical decision.
- If a rule says to ask before a Fable dispatch that neither the user nor the defaults of this workflow chose, do not ask. Use Opus, and name the step in the final report.
- With `--interactive`, every gate stops and waits for the user, as the gate text says.
- When this workflow runs another workflow and this run has `--interactive`, pass the flag on.

## Steps

1. **Parse arguments**

   Extract the change name and optional phase filter from the arguments. If no arguments, use the **AskUserQuestion tool** to ask which change to implement.

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
   - **Follow existing patterns** in the codebase — read related files before writing new code.
   - **If unclear about something, ask the user** — do NOT improvise. This is critical.
   - Use skills from `.claude/` folder for appropriate actions (e.g., `create-domain-model`, `create-tests`, etc.).
   - Mark each task complete in `tasks.md` as you finish it: `- [ ]` → `- [x]`
   - Keep OpenSpec artifacts in sync — if you discover inconsistencies or issues, update the relevant artifacts (specs, design, tasks).
   - Once this change is approved and its behavior is implemented, the canonical/living spec lives
     under `openspec/specs/` — update it there, in place. Do not retroactively back-fill completed
     work into the `openspec/changes/<name>/` folder after the fact: that folder is the transient
     proposal/staging area for work not yet merged into the living spec, not a permanent record.
     (A team convention, not something the OpenSpec tooling enforces.)

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase:
   - Stage the files relevant to that phase by explicit path — never `git add -A`/`.`.
   - Commit with message format: `Phase N: Task X.Y - brief description (5-10 words)`
     - If the plan has no phases, use: `Task X - brief description`
     - If no task numbering either, use: `brief description of changes`
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do NOT push unless `--commit-push` was explicitly specified.

6. **Save research and findings**

   After completing the selected phases (or if stopping due to a blocker), save session context by following the `/save-context` command logic with `--change "<name>"` (plus `--interactive` for a run that has it).
   - If `--context <path>` was specified, save to that path; otherwise fallback to `Notes/Results/<change-name>-research.md`
   - Include: what was done, decisions made, issues found, what's next.
   - This includes `save-context`'s next-session continuation prompt, emitted after Step 7's summary below.

7. **Output results**

   Summarize to the user:
   - Tasks completed this session
   - Overall progress (N/M tasks)
   - Any issues or blockers encountered
   - Key decisions made
   - What to do next

## Guardrails

- **Do NOT improvise** when uncertain — ask the user for clarification
- Follow existing codebase patterns — read before writing
- Keep OpenSpec artifacts in sync with reality
- Use any matching plugin skills for standard operations
- Stop after the specified phases — don't continue into unselected phases
- Always save research findings before stopping
- If implementation reveals design issues: without `--interactive`, update the artifacts for a clear fix, and list the change in the output. If the fix needs a critical decision, ask the user (see "Autonomy"). With `--interactive`, pause and suggest artifact updates.
