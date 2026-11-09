---
name: feature-pipeline
description: Runs one task, from a task provider or a plain request, through a gated pipeline. One subagent runs each stage from requirements to the PR, in an isolated git worktree.
argument-hint: <task-id or "request"> [--dry-run] [--no-worktree] [--start-from=<stage>] [--skip=<stage>] [--model-override=<stage>:<model>] [--commit-mode=<per-step|finalization>] [--interactive] [--autonomous]
when_to_use: "If the user names the feature pipeline, for example 'run the feature pipeline on issue 123', use it. Otherwise, do not use it, also not for a small edit. For one task without the pipeline, use research-implement-review-report or implement-task. For N related tasks, use implement-batch."
---
# Feature Pipeline

Implement one task end-to-end with an implementation-first pipeline of subagents in an isolated git worktree. The task is a tracked task or a plain request.

After a compaction, Claude Code keeps only the first part of this file. If a step is no longer in your context, read this file again from the skill folder before you do the step. Do the same for a reference file that a step names.

## Overview

The master agent (you) runs 10 stages, each in its own subagent with a fresh context. The prompt of each stage is the file `stages/<stage key>.md`. Each stage reads and writes files in `{ARTIFACTS_DIR}/{TASK_ID}/`.

| # | Stage key | Agent type | Default model |
| --- | --- | --- | --- |
| 1 | `requirements` | `general-purpose` | `opus` |
| 2 | `spec` | `general-purpose` | `opus` |
| 2b | `plan-artifact` | `general-purpose` | `sonnet` |
| 3 | `implementation` | `general-purpose` | `sonnet` |
| 4 | `test-coverage` | `general-purpose` | `sonnet` |
| 5 | `simplifier` | `code-simplifier:code-simplifier` | `sonnet` |
| 6 | `docs` | `general-purpose` | `sonnet` |
| 7 | `review` | `general-purpose` | `opus` |
| 8 | `security-review` | `general-purpose` | `opus` |
| 9 | `finalization` | `general-purpose` | `sonnet` |

Stages 6, 7, and 8 run in parallel. "Stage files" in [references/stage-launch.md](references/stage-launch.md) lists the files that each stage reads and writes.

The skill folder is `${CLAUDE_SKILL_DIR}`. The starter context file is `${CLAUDE_SKILL_DIR}/project-context.template.md`.

Run order:

1. Step 0: setup
2. Steps 1, 2, and 2b
3. Human Approve #1, then Task Comment #1
4. Step 3, then the Build Gate
5. Steps 4 and 5, then Steps 6, 7, and 8 in parallel
6. Human Approve #2, then Task Comment #2
7. Step 9, then Step 10: cleanup

Human Approve #1 stops only with `--interactive`. Human Approve #2 stops without `--autonomous`, because it approves the posts, the push, and the PR.

The model defaults are the tier choices of this pipeline. They follow the model matrix in the "Model selection" section of `dev-essentials:subagent-orchestration`. That section has the rules for Haiku and Fable.

Stage 5 needs the external plugin `code-simplifier`. If it is missing, install it, or skip the stage with `--skip=simplifier`. The run then has no output from that stage. Stage 2b uses `dev-essentials:create-html-artifact`, which ships with this plugin.

## Arguments

- Arguments of this run: `$ARGUMENTS`
- The task: the text before the flags at the end. It is a task ID, for example `TASK-123`, or a plain request. Required. "Task input" in [references/setup.md](references/setup.md) says how the run tells them apart.
- `--dry-run`: make the plan only. Create no worktree and no branch, write no file, and run no stage.
- `--no-worktree`: create no worktree. Work on the current branch in the current working directory.
- `--start-from=<stage>`: resume the pipeline at the named stage.
- `--skip=<stage>`: skip a stage. Separate more than one stage with commas.
- `--model-override=<stage>:<model>`: use another model for a stage. Separate more than one entry with commas, for example `--model-override=review:sonnet,spec:sonnet`.
- `--commit-mode=<per-step|finalization>`: the commit cadence of the run. The default is `finalization`. See "Commit Cadence".
- `--interactive`: stop at Human Approve #1, and ask before each fix round of Human Approve #2. See "Autonomy".
- `--autonomous`: do not stop at Human Approve #1 or #2. Post the task comments, push, and open the PR without a question. See "Autonomy".

The stage names are the stage keys in the Overview table. The valid models are `opus`, `sonnet`, `haiku`, and `fable`. A `--model-override=<stage>:fable` that the user typed is its own approval, because the explicit choice of the user outranks the matrix. For a Fable choice on the own initiative of the master agent, see "Autonomy". Both rules follow the "Model selection" section of `dev-essentials:subagent-orchestration`.

## Autonomy

This workflow has three modes. The user picks one with a flag: the default (no flag), `--interactive`, or `--autonomous`. A gate is a step where the run can stop and ask the user. This table lists each gate of this workflow and what each mode does there.

| Gate | Default | `--interactive` | `--autonomous` |
| --- | --- | --- | --- |
| Human Approve #1 | Report the paths, and continue | Stop | Same as default |
| Human Approve #1: open decisions in `spec.md` | Ask | Ask | Decide, and write each one into `spec.md` |
| Stage questions of Stages 1 and 2 | Ask | Ask | Take the recommended option |
| Task Comment #1 | Post it at Human Approve #2 | Post it now | Post it now |
| Fix round for blocking issues | Run one round with no stop | Ask before each round | Same as default |
| Human Approve #2 (posts, push, PR) | Stop | Stop | No stop, unless blocking issues remain after the fix round |
| `--no-worktree` on the default branch, the base branch, or a detached HEAD | Ask | Ask | Create the branch of sub-step 5 in `references/setup.md` |
| Step 10: worktree removal | Only after the PR merges, or on a request of the user | Same | Same |
| Step 10: the PR lookup fails | Stop and ask | Same | Skip the archive and the worktree removal, and report the lookup |
| Fable on the own initiative of the agent | Use Opus, and name the stage in the final report | Ask before each Fable dispatch | Same as default |

These rules apply in every mode:

- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that the run cannot fix also stops the run. Do not ask in other cases.
- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default of the gate, and continue.
- The final report lists each gate that the run passed without a stop. With `--autonomous`, it also lists each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It adds no steps. A step that runs only with a flag such as `--push` still needs that flag, and the flag is the approval of that step.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.
- With `--autonomous`, do not destroy git work that has no other copy. Examples: a branch with unmerged commits, or a worktree with uncommitted changes. List such an action in the final report instead.

## Pipeline Discipline

Three safeguards apply to you and to every stage: claims about Claude Code, schema and configuration errors, and an MCP failure. Their text is in [references/pipeline-discipline.md](references/pipeline-discipline.md). Read it at Step 0. Each stage prompt gets the text word for word (see "Stage Launch").

## Commit Cadence

Five stages can commit: `implementation` (also in the fix rounds of Human Approve #2, which run this stage again), `test-coverage`, `simplifier`, `docs`, and `finalization`. No other stage commits. Stage 2b does not touch git.

- `finalization` mode (default): each stage stages only its own changes with an explicit `git add <path>`, never `-A` or `.`. It does not commit. Stage 9 creates the one commit of the run. Then the master agent pushes and opens the PR (Step 9).
- `per-step` mode: each of the four earlier stages commits its own changes as soon as they are green. Each stage file states its own commit granularity. Stage 9 creates no commit. If `git status` shows uncommitted or unstaged source changes when Stage 9 starts, Stage 9 stops and reports. It does not commit them. The start-change paths that no stage edited do not count.

In both modes, only the master agent pushes, at Step 9 after Stage 9, never between commits. It never force-pushes, never passes `--no-verify`, and does not push the default branch (Step 9). Never commit anything under `{ARTIFACTS_DIR}/`.

Each commit-capable stage gets `{COMMIT_MODE}` and the `<commit-conventions>` block of [references/commit-conventions.md](references/commit-conventions.md) in its prompt (see "Stage Launch").

## Stage Launch

Before you launch a stage, read [references/stage-launch.md](references/stage-launch.md), and do its launch steps. They compose the prompt from the blocks of Step 0 and replace the four placeholders: `{TASK_ID}`, `{WORKTREE_PATH}`, `{ARTIFACTS_DIR}`, and `{COMMIT_MODE}`. After each stage, do the steps of "After the stage" in the same file. They read the final reply, handle the questions of Stages 1 and 2, and run the output check.

## Checkpoints

The master agent keeps `{ARTIFACTS_DIR}/{TASK_ID}/pipeline-state.json` up to date during the whole run. Read [references/checkpoint-protocol.md](references/checkpoint-protocol.md) at Step 0. It has the schema, the notes for each field, the updates during the run, and the resume checks. After each write and at each load on a resume, check the file as that reference says. If the file is not valid JSON, stop. On a resume, "Updates during the run" in that file decides the first stage, and the gate or the comment that runs before it.

## Orchestration

### Step 0: Setup

Read [references/setup.md](references/setup.md), and do its sub-steps 1 to 15. They parse the arguments, load the project context, fetch the task (for a task ID), and set up the worktree. They also write `task-context.md`, load or create `pipeline-state.json` with the resume checks, and resolve `{COMMIT_MODE}`. With `--dry-run`, Step 0 creates and writes nothing, and the run ends after Step 0.

### Steps 1, 2, and 2b

Launch the stages `requirements`, `spec`, and `plan-artifact`, one after the other.

Stage 2b does not block the pipeline. A broken renderer must never keep the run from Human Approve #1. Its retry and its checkpoint are in "After the stage" of [references/stage-launch.md](references/stage-launch.md).

### Human Approve #1 (after Spec)

Without `--interactive`, report the paths of `spec.md`, `test-plan.md`, and the HTML artifact in one status line, and continue. If `spec.md` lists open decisions without a resolution, first ask the user about them. With `--autonomous`, decide them as "Autonomy" says, and write each decision into `spec.md`.

With `--interactive`, show the user:

- A summary of `{ARTIFACTS_DIR}/{TASK_ID}/spec.md`
- A summary of `{ARTIFACTS_DIR}/{TASK_ID}/test-plan.md`
- The path of the HTML artifact (`{ARTIFACTS_DIR}/{TASK_ID}/{TASK_ID}-implementation-plan.html`) to open in a browser, or a note that its render failed or was skipped

Then ask this question: "Approve spec and proceed to implementation? (yes / edit feedback)".

> **Anti-bypass clause (with `--interactive`).** This gate stands on its own. A general instruction to work without clarifying questions does **not** let you skip this gate. The same holds for an instruction to "make the reasonable call and continue". Such an instruction settles an ambiguity. This gate is a consent point that exists to get the explicit approval of the user.
>
> **Counts as explicit approval to skip the gate.** Only these phrases or a clear equivalent count. The user must type one in this session: "approve all gates", "auto-approve the pipeline", "skip Human Approve #1/#2", "I trust you, run end-to-end".
>
> **Does not count**, and the gate stays armed: "no clarifying questions" and "make the reasonable call". A bare "continue" or "ok" from an unrelated context does not count either. Neither does an approval that the agent infers or makes up.
>
> At each gate, use `AskUserQuestion`, or stop and wait. Never act on a paraphrase of "the user said to continue".

If the user gives feedback, run the `spec` stage again with the feedback in its prompt. If the user approves, continue.

### Task Comment #1 (before Implementation)

If `taskSource` is `request`, the run has no task to comment on. Skip Task Comment #1 and #2 in every mode, and say so in the final report.

In the default mode, do not post this comment now. Write it to `{ARTIFACTS_DIR}/{TASK_ID}/task-comment-1.md`. Post it at Human Approve #2, after the yes of the user and before Task Comment #2. Then write "implementation started" in the past tense. With `--interactive` or `--autonomous`, post it now.

Write and post the comment as [references/task-comments.md](references/task-comments.md) says. If the post fails, stop at once.

### Step 3: Implementation

Launch the stage `implementation`.

### Build Gate (after Implementation)

The master agent runs this gate. It gives the build to the agent type `dev-essentials:test-runner`, and reads only its report. The gate is not a stage, so `--model-override` does not apply to it.

1. Dispatch `dev-essentials:test-runner` with the absolute path `{WORKTREE_PATH}` and the words "build only". Also give it the build command from the project context, for example the `dotnet build ...` line under Commands.
2. If the status is GREEN, update the checkpoint, and continue with Step 4.
3. If the status is RED, do the steps of "Build Gate retry" in [references/stage-launch.md](references/stage-launch.md). If the build fails after 2 attempts in total, stop the pipeline, and report the build errors to the user. Do not continue to `test-coverage` with broken code.
4. Record the result of the gate (`pass`, `pass-after-retry`, or `fail`) in `buildGate` of `pipeline-state.json`.

### Steps 4 and 5: Test Coverage and Code Simplifier

Launch the stage `test-coverage`, then the stage `simplifier`.

### Steps 6, 7, and 8: Docs, Code Review, and Security Review (parallel)

Launch the stages `docs`, `review`, and `security-review` at the same time, with three `Agent` calls in one message. Before the launch of the two reviews, write their patch as "Review patch" in [references/stage-launch.md](references/stage-launch.md) says. If the fetch fails, stop and ask the user. Wait until all three are done, then update the checkpoint.

### Human Approve #2 (after Review)

This gate stops without `--autonomous`, because it approves the posts to the task provider, the push, and the PR of Step 9. With `--autonomous`, write the gate content to the final report, and continue to Task Comment #2. If Task Comment #1 is not posted yet, post it first. One exception: if blocking issues remain after the automatic fix round, stop and show this gate in every mode. The run cannot fix them itself.

"Blocking issues in the reviews" means the items under `## Blocking Issues` in `review.md` and in `security-review.md`.

Show the user:

- The contents of `{ARTIFACTS_DIR}/{TASK_ID}/review.md`
- The contents of `{ARTIFACTS_DIR}/{TASK_ID}/security-review.md`
- A summary of the git diff: the changed files and the added and removed lines

If the run skipped `review` or `security-review`, show "skipped" in place of its file. The blocking issues then come only from the review file that exists.

Then ask this question: "Approve finalization (task comments, push, PR)? (yes / request changes)". For a request, ask "Approve finalization (push, PR)? (yes / request changes)".

The anti-bypass clause of Human Approve #1 applies to this gate too, also in the default mode. The same lists of phrases count and do not count.

Run a fix round, as "Fix round" in [references/stage-launch.md](references/stage-launch.md) says, in these cases:

- The reviews have blocking issues, the run has no `--interactive`, and `autoFixRound` in `pipeline-state.json` is not `true`. Run this round before you show the gate.
- The user asks for a fix round (request changes).

If the user approves, continue.

### Task Comment #2 (before Finalization)

For a request, skip this comment (see Task Comment #1). Else, before you launch Step 9, write and post a second comment as [references/task-comments.md](references/task-comments.md) says. If the post fails, stop at once.

### Step 9: Finalization + PR

Launch the stage `finalization`. It makes the commit and reports the facts for the push and the PR. It does not push. Then run the push and the PR yourself, in the main session. A push stays with the main agent (`dev-essentials:subagent-orchestration` Rule 4), so that the user sees the push command and its result. Human Approve #2 approved both, or `--autonomous` did.

1. Push. If the report gives no push command, say so in the final report, and do not invent a push step. If the current branch is the default branch of the repository, do not push. Stop and report it. Else run `cd "{WORKTREE_PATH}" && <push command>`. Never force-push, and never pass `--no-verify`. If the push fails because the history diverged, stop and report it.
2. Create the PR. If the report gives no PR command, skip this step. Report the branch status and the work that is left for the human. If the PR command is a shell command, run `cd "{WORKTREE_PATH}" && <PR command>`. If it is an MCP tool name, load the tool with `ToolSearch`. Then call it with the base branch, the title, and the body of the report.
3. If the report names a linking tool, link the PR to its tracking issue. Load the tool with `ToolSearch`, and create the link. If the link fails, report the failure, and continue, because the PR exists. Without a linking tool, the task URL in the PR body is the link.
4. If step 1 or step 2 fails, stop and report the failure. Do not try workarounds.

Add `finalization` to `completed` only after these steps. Put the "Not committed" list of the stage into the final report. Then update the checkpoint, and report the branch or PR status.

If the run created a PR, write its `number`, `url`, `owner`, and `repo` into `pr` of `pipeline-state.json` before Step 10. If it created no PR (a branch-only flow, or no PR command), leave `pr` as `null`.

### Step 10: Cleanup

After the result of Step 9 is final, read [references/cleanup.md](references/cleanup.md), and do its steps. Do not archive the task logs or remove the worktree before you read it. By default, the worktree and the artifacts stay until the PR is merged.
