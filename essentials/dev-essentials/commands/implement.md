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
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
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
   - **If unclear about something, ask the user**. Do NOT improvise. With `--autonomous`, decide as "Autonomy" says.
   - Use the skills that fit the change type, for example `create-domain-model` and `create-tests`.
   - Mark each task complete in the plan file as you finish it: `- [ ]` → `- [x]`

5. **Commit changes** (if `--commit` or `--commit-push`)

   After completing each phase/section:
   - Stage the files relevant to that phase by explicit path. Never use `git add -A` or `git add .`.
   - Commit with message format: `Phase N: Task X.Y - brief description (5-10 words)`
     - If the plan has no phases, use: `Task X - brief description`
     - If no task numbering either, use: `brief description of changes`
   - If `--commit-push`, also push to the current remote tracking branch.
   - Do NOT push unless `--commit-push` was explicitly specified.

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

- **Do NOT improvise**. If you are not sure, ask the user for clarification. With `--autonomous`, decide as "Autonomy" says.
- Stop after the specified sections. Do not continue into sections that the user did not select.
- Always save research findings before stopping
- If implementation reveals plan issues: without `--interactive`, update the plan for a clear fix, and list the change in the output. If the fix needs a critical decision, follow "Autonomy". With `--interactive`, pause and suggest updates.
- The plan file is the single source of truth. Keep it up to date.
