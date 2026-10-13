---
name: feature-pipeline
description: Runs a tracked task from a task provider end-to-end in an isolated git worktree. Each stage (requirements, spec, implementation, tests, docs, reviews, and the PR) runs in its own subagent. Use it to implement a tracked task or TASK-123, or to develop a feature end-to-end. Also for "run the feature pipeline", "run feature-pipeline", or "start the task pipeline for TASK-123".
argument-hint: <task-id> [--dry-run] [--no-worktree] [--start-from=<stage>] [--skip=<stage>] [--model-override=<stage>:<model>] [--commit-mode=<per-step|finalization>] [--interactive] [--autonomous]
disable-model-invocation: true
---
# Feature Pipeline

Implement a tracked task end-to-end with an implementation-first pipeline of subagents in an isolated git worktree.

## Overview

The master agent (you) runs 10 stages, each in its own subagent with a fresh context. The prompt of each stage is the file `stages/<stage key>.md`. Each stage reads and writes files in `{ARTIFACTS_DIR}/{TASK_ID}/`.

| # | Stage key | Agent type | Default model | Reads | Writes |
| --- | --- | --- | --- | --- | --- |
| 1 | `requirements` | `general-purpose` | `opus` | Task context only | `requirements.md` |
| 2 | `spec` | `general-purpose` | `opus` | `requirements.md` | `spec.md`, `test-plan.md` |
| 2b | `plan-artifact` | `general-purpose` | `sonnet` | `requirements.md`, `spec.md`, `test-plan.md` | `{TASK_ID}-implementation-plan.html` |
| 3 | `implementation` | `general-purpose` | `sonnet` | `requirements.md`, `spec.md`, `test-plan.md`, and `review-feedback.md` on a re-entry | Code and tests |
| 4 | `test-coverage` | `general-purpose` | `sonnet` | `requirements.md`, `spec.md`, `test-plan.md` | Test files |
| 5 | `simplifier` | `code-simplifier:code-simplifier` | `sonnet` | The diff against the base branch | Code |
| 6 | `docs` | `general-purpose` | `sonnet` | `requirements.md`, `spec.md` | Docs |
| 7 | `review` | `feature-dev:code-reviewer` | `opus` | `requirements.md`, `spec.md`, `test-plan.md` | `review.md` |
| 8 | `security-review` | `general-purpose` | `opus` | `requirements.md`, `spec.md` | `security-review.md` |
| 9 | `finalization` | `general-purpose` | `sonnet` | `requirements.md`, `spec.md`, `review.md` | Commit, push, and PR |

Every stage also gets the task context (`task-context.md`, injected). Stages 6, 7, and 8 run in parallel.

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

Stages 5 and 7 need the external plugins `code-simplifier` and `feature-dev`. Install both before a run. If one is missing, install it, or skip its stage with `--skip=simplifier` or `--skip=review`. The run then has no output from that stage. Stage 2b uses `dev-essentials:create-html-artifact`, which ships with this plugin.

## Arguments

- `$ARGUMENTS[0]`: the task ID, for example `TASK-123`. Required.
- `--dry-run`: make the plan only. Write no code.
- `--no-worktree`: create no worktree. Work on the current branch in the current working directory.
- `--start-from=<stage>`: resume the pipeline at the named stage.
- `--skip=<stage>`: skip a stage. Separate more than one stage with commas.
- `--model-override=<stage>:<model>`: use another model for a stage. Separate more than one entry with commas, for example `--model-override=review:sonnet,spec:sonnet`.
- `--commit-mode=<per-step|finalization>`: the commit cadence of the run. `finalization` (default) makes one commit at Stage 9. With `per-step`, each stage commits its own changes as soon as they are green. See "Commit Cadence".
- `--interactive`: stop at Human Approve #1, and ask before each fix round of Human Approve #2. See "Autonomy".
- `--autonomous`: do not stop at Human Approve #1 or #2. Post the task comments, push, and open the PR without a question. See "Autonomy".

The stage names are the stage keys in the Overview table. The valid models are `opus`, `sonnet`, `haiku`, and `fable`. A `--model-override=<stage>:fable` that the user typed is its own approval, because the explicit choice of the user outranks the matrix. If the master agent picks Fable on its **own** initiative, then with `--interactive`, ask the user first, every time. Without `--interactive`, keep the default model of the stage (see "Autonomy"). Both rules follow the "Model selection" section of `dev-essentials:subagent-orchestration`.

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
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. Delete such a branch with `git branch -D` only if both checks pass. First, its pull request is merged. Find the pull request with `list_pull_requests` (branch as `head`), then read it with `pull_request_read`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the pull request state cannot be read, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Pipeline Discipline

These three safeguards apply to every stage. The subagents of this pipeline MUST follow them too.

### Safeguard 1: claims about Claude Code

Before you state how a Claude Code feature works, read the current system prompt. Do not match patterns from training data. Examples: Skill tool dispatch, Agent tool subagent types, and the merge order of settings. More examples: MCP tool prefixes, plugin loading, slash-command routing, and the memory system. The system prompt is the source of truth for the session, and it changes between Claude Code versions. If you are not sure, say so and look it up. Do not state a categorical rule. See `dev-essentials:engineering-discipline` for the wider rule.

### Safeguard 2: schema, manifest, and configuration errors

At any stage, you can find a schema error, a failed manifest validation, or a mismatch with a library API. Before you propose a fix, find the cause in a primary source: the official docs or a known-working example, for example the plugin `feature-dev`. Until then, call your diagnosis a theory ("this can be ..."), not a fix. See `dev-essentials:subagent-orchestration` for the quality of briefs.

### Safeguard 3: an MCP failure

If the MCP server of the task provider fails, answer two questions before you look at the install state or advise a restart:

1. Does the server fail only in this session, or also in other Claude sessions that run at the same time?
2. Which terminal hosts Claude Code? Warp and other sandboxed terminals isolate MCP child processes.

If the host can isolate subprocesses, advise a plain OS terminal (cmd, pwsh, or Windows Terminal), not a restart in place.

## Commit Cadence

Five stages can commit: `implementation` (also in the fix rounds of Human Approve #2, which run this stage again), `test-coverage`, `simplifier`, `docs`, and `finalization`. No other stage commits. Stage 2b does not touch git.

- `finalization` mode (default): each stage stages only its own changes with an explicit `git add <path>`, never `-A` or `.`. It does not commit. Stage 9 creates the one commit of the run, pushes, and opens the PR.
- `per-step` mode: each of the four earlier stages commits its own changes as soon as they are green. Each stage file states its own commit granularity. Stage 9 creates no commit. If `git status` shows uncommitted or unstaged source changes at the start of Stage 9, Stage 9 stops and reports. It does not commit them.

In both modes, push only at Stage 9, never between commits. Never commit anything under `{ARTIFACTS_DIR}/`.

State `{COMMIT_MODE}` explicitly in the prompt of each commit-capable stage. Do not expect a subagent to infer it. Each commit-capable stage also gets the `<commit-conventions>` block. The block and its rules are in [references/commit-conventions.md](references/commit-conventions.md).

## Stage Launch

Before you launch a stage, do these steps in order:

1. Make sure that each file in the "Reads" column of the Overview table exists. If a file is missing, stop and name the missing files. This matters most after a `--start-from` that skipped earlier stages.
2. Resolve the model. If this invocation has a `--model-override` entry for this stage, use it. Else use the entry of this stage in `models` of `pipeline-state.json`, from an earlier run. Else use the default model of the Overview table. Write the result into `models` (`{"<stage>": "<model>"}`). If an override of this invocation replaces a recorded entry, log the change. Pass the model in the `model` parameter of the `Agent` tool.
3. For a commit-capable stage, write the output of `git rev-parse HEAD` into `stageStartSha` (`{"<stage>": "<sha>"}`). This records the branch tip at the start of the stage. A later resume uses it to find out whether HEAD moved while the stage was incomplete.
4. Compose the prompt. Put these blocks above the text of the stage file, in this order. `<commit-conventions>` goes only to the five commit-capable stages.

   ```md
   <project-context>
   {resolved project context}
   </project-context>

   <task-context>
   {contents of {ARTIFACTS_DIR}/<task-id>/task-context.md}
   </task-context>

   <commit-conventions>
   {the block from references/commit-conventions.md, with its cadence line for {COMMIT_MODE}}
   </commit-conventions>

   {text of the stage file}
   ```

5. Replace the four placeholders in the composed prompt:
   - `{TASK_ID}`: the task ID.
   - `{WORKTREE_PATH}`: the absolute path of the project root. This is the worktree path, or the current working directory with `--no-worktree`.
   - `{ARTIFACTS_DIR}`: the repository-relative folder for the pipeline artifacts, for example `tasks` or `Notes/Tasks`.
   - `{COMMIT_MODE}`: the resolved commit cadence, `per-step` or `finalization`.
6. Make sure that no placeholder is left as a literal string in the composed prompt. `{CADENCE_LINE}` must also be gone. If one is left, stop, and name the placeholder and the stage.

After each stage, run the output check (see "Output Validation"). Then update the checkpoint (see "Checkpoints").

The master agent writes `review-feedback.md` before it runs `implementation` again (Build Gate, or a fix round of Human Approve #2). If the file exists, the implementation stage knows that the run is a re-entry.

## Output Validation

After each stage, and before you update the checkpoint, check the files that the stage wrote. This finds structural problems before later stages read bad input.

| File | Required headings |
| --- | --- |
| `requirements.md` | `## 1. Task Summary`, `## 2. Scope`, `## 3. Acceptance Criteria`, `## 4. Technical Constraints`, `## 5. Open Questions & Recommendations`, `## 6. Risks & Considerations` |
| `spec.md` | `## 1. Resolved Questions`, `## 2. Architecture Overview`, `## 3. Implementation Steps`, `## 4. Execution Order`, `## 6. Edge Cases & Error Handling` |
| `test-plan.md` | `## 1. Test Strategy Overview`, `## 2. Test Cases`, `## 3. Tests for Existing Code`, `## 4. Coverage Expectations` |
| `review.md` | `## Blocking Issues`, `## Warnings`, `## Suggestions`, `## Summary` |
| `security-review.md` | `## Blocking Issues`, `## Warnings`, `## Summary` |

1. Read the file after the stage is done.
2. Find each required heading. The match ignores case.
3. If a heading is missing, log the missing headings. Run the same stage again with this feedback: "Your output is missing required sections: [list]. Rewrite the file with all required sections."
4. Allow 1 retry for the structure. If the file fails again, stop the pipeline, and report the malformed output to the user.
5. Do not look for optional headings, such as `## 5. Database Migrations` in `spec.md`. They can be absent.

## Checkpoints

The master agent keeps `{ARTIFACTS_DIR}/{TASK_ID}/pipeline-state.json` up to date during the whole run. Its schema, the notes for each field, and the two resume checks are in [references/checkpoint-protocol.md](references/checkpoint-protocol.md). Read that file at Step 0.

- After each write and at each load on a resume, check the file as that reference says. If the file is not valid JSON, stop.
- After each successful stage, update `stage` and `completed`. After each posted task comment, update `taskComments`.
- On a resume, start at the first stage that is not in `completed`. `--start-from=<stage>` overrides this resume point. `--skip=<stage>` removes the stage from the plan.
- If an earlier stage runs again and it can change code or docs, first remove all later dependent stages from `completed`.
- If `spec` runs again, also remove `plan-artifact` from `completed`, so that the HTML artifact renders again from the new spec.
- If `requirements` or `spec` runs again, clear both task-comment checkpoints, so that both comments post fresh summaries.
- If a code, test, docs, review, or security stage runs again after Task Comment #2 was posted, clear only the checkpoint of Task Comment #2.
- If Step 3 or a later stage will run and `taskComments.analysisPostedAt` is missing, post Task Comment #1 first. In the default mode, Human Approve #2 posts it instead.
- If Step 9 will run and `taskComments.preFinalizationPostedAt` is missing, post Task Comment #2 first.

## Orchestration

After a compaction, Claude Code keeps only the first part of this file. If a step below is no longer in your context, read this `SKILL.md` again from the skill folder before you do the step.

### Step 0: Setup

Read [references/setup.md](references/setup.md), and do its sub-steps 1 to 15. They parse the arguments, load the project context, fetch the task, and set up the worktree. They also write `task-context.md`, load or create `pipeline-state.json` with the resume checks, and resolve `{COMMIT_MODE}`. With `--dry-run`, the run ends after Step 0.

### Steps 1, 2, and 2b

Launch the stages `requirements`, `spec`, and `plan-artifact`, one after the other.

Stage 2b does not block the pipeline. A broken renderer must never keep the run from Human Approve #1. The stage failed in two cases: its final output has no `ARTIFACT: <path>` line, or the named file does not exist. If it failed, run it once more. If it fails again, log a warning, and continue without the artifact. Add `plan-artifact` to `completed` after each of the three outcomes: success, success at the retry, or give-up. Then a resume does not try a broken render again. Also record `planArtifact` (see the schema).

### Human Approve #1 (after Spec)

Without `--interactive`, report the paths of `spec.md`, `test-plan.md`, and the HTML artifact in one status line, and continue. If `spec.md` lists open decisions without a resolution, first ask the user about them. With `--autonomous`, decide them as "Autonomy" says, and write each decision into `spec.md`.

With `--interactive`, show the user:

- A summary of `{ARTIFACTS_DIR}/{TASK_ID}/spec.md`
- A summary of `{ARTIFACTS_DIR}/{TASK_ID}/test-plan.md`
- The path of the HTML artifact (`{ARTIFACTS_DIR}/{TASK_ID}/{TASK_ID}-implementation-plan.html`) to open in a browser, or a note that its render failed or was skipped

Then ask this question: "Approve spec and proceed to implementation? (yes / edit feedback)".

> **Anti-bypass clause (with `--interactive`).** This gate stands on its own. A general instruction to work without clarifying questions does **NOT** let you skip this gate. The same holds for an instruction to "make the reasonable call and continue". Such an instruction settles an ambiguity. This gate is a consent point that exists to get the explicit approval of the user.
>
> **Counts as explicit approval to skip the gate.** Only these phrases or a clear equivalent count. The user must type one in this session: "approve all gates", "auto-approve the pipeline", "skip Human Approve #1/#2", "I trust you, run end-to-end".
>
> **Does NOT count**, and the gate stays armed: "no clarifying questions" and "make the reasonable call". A bare "continue" or "ok" from an unrelated context does not count either. Neither does an approval that the agent infers or makes up.
>
> At each gate, use `AskUserQuestion`, or stop and wait. Never act on a paraphrase of "the user said to continue".

Without `--interactive`, the default approval of "Autonomy" applies. In the default mode, the push, the PR, and the task comments still wait for Human Approve #2. With `--autonomous`, they do not wait, because the user chose that with the flag. A general instruction such as "no clarifying questions" is not that flag.

If the user gives feedback, run the `spec` stage again with the feedback in its prompt. If the user approves, continue.

### Task Comment #1 (before Implementation)

Without `--interactive` or `--autonomous`, do not post this comment now. Write it to `{ARTIFACTS_DIR}/{TASK_ID}/task-comment-1.md`. Post it at Human Approve #2, after the yes of the user and before Task Comment #2. Then write "implementation started" in the past tense. With `--interactive`, post it now, because the approval at Human Approve #1 covers it. With `--autonomous`, post it now.

The comment summarizes:

- The task objective in plain English
- The approved implementation approach from `spec.md`
- The planned test strategy from `test-plan.md`
- The key constraints, risks, or migrations that the analysis names
- That the implementation starts now
- A footer line: "This comment was generated by Claude Code"

Both task comments follow these rules. Write the comment in English, and keep it short. Post it to the task through the MCP server of the task provider. If the provider supports Markdown comments, use short headings and flat bullets. Else post the same content as plain text. If the post fails, stop at once. After a successful post, record the time and the comment ID of the provider (if one exists) in `taskComments` of `pipeline-state.json`.

### Step 3: Implementation

Launch the stage `implementation`.

### Build Gate (after Implementation)

The master agent runs this gate itself, without a subagent.

1. Run the build command from the project context, for example the `dotnet build ...` line under Commands.
2. If the build succeeds, update the checkpoint, and continue with Step 4.
3. If the build fails:
   - Write the first 50 error lines of the build output to `{ARTIFACTS_DIR}/{TASK_ID}/review-feedback.md`, with an instruction to fix the compilation only: no new features and no refactoring.
   - Run the implementation stage again. It finds the feedback file.
   - Run the build command again.
   - If the build fails after 2 attempts in total, stop the pipeline, and report the build errors to the user. Do not continue to `test-coverage` with broken code.
4. Record the result of the gate (`pass`, `pass-after-retry`, or `fail`) in `buildGate` of `pipeline-state.json`.

The gate keeps the test-coverage agent from spending its whole budget on compile errors.

### Steps 4 and 5: Test Coverage and Code Simplifier

Launch the stage `test-coverage`, then the stage `simplifier`. The simplifier is a plugin agent with its own simplification logic. Its stage file only adds the scope and the test rules of the pipeline.

### Steps 6, 7, and 8: Docs, Code Review, and Security Review (parallel)

Launch the stages `docs`, `review`, and `security-review` at the same time, with three `Agent` calls in one message. The reviewer is a plugin agent with its own review logic. Its stage file only adds the context and the output format. The security stage file holds its full method. Wait until all three are done, then update the checkpoint.

### Human Approve #2 (after Review)

This gate stops without `--autonomous`, because it approves the posts to the task provider, the push, and the PR of Stage 9. With `--autonomous`, write the gate content to the final report, and continue to Task Comment #2. If Task Comment #1 is not posted yet, post it first. One exception: if blocking issues remain after the automatic fix round, stop and show this gate in every mode. The run cannot fix them itself. Without `--interactive`, and with blocking issues in the reviews, run one automatic fix round (the numbered steps below) before you show this gate. If the reviews still have blocking issues after that round, show this gate with the open blocking issues. If the user asks for a fix round (request changes), start one.

"Blocking issues in the reviews" means the items under `## Blocking Issues` in `review.md` and in `security-review.md`.

Show the user:

- The contents of `{ARTIFACTS_DIR}/{TASK_ID}/review.md`
- The contents of `{ARTIFACTS_DIR}/{TASK_ID}/security-review.md`
- A summary of the git diff: the changed files and the added and removed lines

Then ask this question: "Approve finalization (task comments, push, PR)? (yes / request changes)".

The anti-bypass clause of Human Approve #1 applies to this gate too, with the same lists of phrases that count and do not count.

Before you run `implementation` again for review findings, apply Safeguard 2 to each finding. This matters most for schema and manifest errors and for claims about library APIs.

If the reviews have blocking issues, run a fix round in these cases:

- The run has no `--interactive`, and `autoFixRound` in `pipeline-state.json` is not `true`.
- The user asks for a fix round (request changes).

Fix round steps:

1. Write the blocking issues of both reviews to `{ARTIFACTS_DIR}/{TASK_ID}/review-feedback.md`. Then run the implementation stage again with this feedback (up to 1 retry).
2. Remove these stages from `completed` in `pipeline-state.json`: `test-coverage`, `simplifier`, `docs`, `review`, `security-review`, and `finalization`. In the same write, set `"autoFixRound": true`. A missing key means `false`.
3. Run Step 4 (Test Coverage) again.
4. Run Step 5 (Code Simplifier) again.
5. Run Steps 6, 7, and 8 again, in parallel.
6. Go back to Human Approve #2 with the fresh review files. Show the gate even with open blocking issues.

If the user approves, continue.

### Task Comment #2 (before Finalization)

Before you launch Step 9, post a second comment. It follows the rules of Task Comment #1 and summarizes:

- What the run implemented
- The added or updated tests, and the latest test status
- Any documentation updates
- The results of the code review and the security review
- That the task moves into finalization next
- A footer line: "This comment was generated by Claude Code"

### Step 9: Finalization + PR

Launch the stage `finalization`. When it is done, update the checkpoint, and report the branch or PR status.

If the stage created a PR, write its `number`, `url`, `owner`, and `repo` into `pr` of `pipeline-state.json` before Step 10. If it created no PR (a branch-only flow, or no PR command), leave `pr` as `null`. Step 10 reads this field to decide whether it needs a GitHub PR lookup.

### Step 10: Cleanup

After the result of Step 9 is final, read [references/cleanup.md](references/cleanup.md), and do its steps. Do not archive the task logs or remove the worktree before you read it. By default, the worktree and the artifacts stay until the PR is merged.
