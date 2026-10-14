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
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If both checks below pass, you can delete such a branch with `git branch -D`. First, its pull request is merged. Find the pull request with `list_pull_requests` (branch as `head`), then read it with `pull_request_read`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the run cannot read the state of the pull request, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
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
   - Use the skills that fit the change type, for example `create-domain-model` and `create-tests`.
   - Mark each task complete in `tasks.md` as you finish it: `- [ ]` → `- [x]`
   - Keep the OpenSpec artifacts in sync with the code. If you find an inconsistency or an issue, update the artifacts that it affects (specs, design, tasks).
   - After this change is approved and its behavior is implemented, the living spec under `openspec/specs/` is the canonical spec. Update it there, in place. Do not back-fill finished work into `openspec/changes/<name>/`. That folder is a staging area for work that is not merged into the living spec yet. It is not a permanent record. This rule is a convention of the team. The OpenSpec tooling does not enforce it.

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase:
   - Stage the files relevant to that phase by explicit path. Never use `git add -A` or `git add .`.
   - Commit with message format: `Phase N: Task X.Y - brief description (5-10 words)`
     - If the plan has no phases, use: `Task X - brief description`
     - If no task numbering either, use: `brief description of changes`
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do NOT push unless `--commit-push` was explicitly specified.

6. **Save research and findings**

   Run this step after the selected phases. If the run stops because of a blocker, run it before the stop. Follow the `/save-context` command logic with `--change "<name>"`, plus `--interactive` or `--autonomous` for a run that has it.
   - If `--context <path>` was given, save to that path. Else save to `Notes/Results/<change-name>-research.md`.
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

- **Do NOT improvise**. If you are not sure, ask the user for clarification. With `--autonomous`, decide as "Autonomy" says.
- Stop after the specified phases. Do not continue into phases that the user did not select.
- Always save research findings before stopping
- If implementation reveals design issues: without `--interactive`, update the artifacts for a clear fix, and list the change in the output. If the fix needs a critical decision, follow "Autonomy". With `--interactive`, pause and suggest artifact updates.
