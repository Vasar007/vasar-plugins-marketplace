---
name: feature-pipeline
description: Runs a tracked task from a task provider end-to-end in an isolated git worktree, with one subagent for each stage from requirements to the PR. Use it for "run the feature pipeline" or "implement TASK-123 end-to-end".
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
| 7 | `review` | `feature-dev:code-reviewer` | `opus` | `requirements.md`, `spec.md`, `test-plan.md`, `review-diff.patch` | Final reply, which the master agent saves as `review.md` |
| 8 | `security-review` | `general-purpose` | `opus` | `requirements.md`, `spec.md` | `security-review.md` |
| 9 | `finalization` | `general-purpose` | `sonnet` | `requirements.md`, `spec.md`, `review.md` | Commit, and the facts for the push and the PR |

Every stage also gets the task context (`task-context.md`, injected). Stages 6, 7, and 8 run in parallel.

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

Stages 5 and 7 need the external plugins `code-simplifier` and `feature-dev`. Install both before a run. If one is missing, install it, or skip its stage with `--skip=simplifier` or `--skip=review`. The run then has no output from that stage. Stage 2b uses `dev-essentials:create-html-artifact`, which ships with this plugin.

## Arguments

- Arguments of this run: `$ARGUMENTS`
- The first argument (`$ARGUMENTS[0]`): the task ID, for example `TASK-123`. Required.
- `--dry-run`: make the plan only. Create no worktree and no branch, write no file, and run no stage.
- `--no-worktree`: create no worktree. Work on the current branch in the current working directory.
- `--start-from=<stage>`: resume the pipeline at the named stage.
- `--skip=<stage>`: skip a stage. Separate more than one stage with commas.
- `--model-override=<stage>:<model>`: use another model for a stage. Separate more than one entry with commas, for example `--model-override=review:sonnet,spec:sonnet`.
- `--commit-mode=<per-step|finalization>`: the commit cadence of the run. `finalization` (default) makes one commit at Stage 9. With `per-step`, each stage commits its own changes as soon as they are green. See "Commit Cadence".
- `--interactive`: stop at Human Approve #1, and ask before each fix round of Human Approve #2. See "Autonomy".
- `--autonomous`: do not stop at Human Approve #1 or #2. Post the task comments, push, and open the PR without a question. See "Autonomy".

The stage names are the stage keys in the Overview table. The valid models are `opus`, `sonnet`, `haiku`, and `fable`. A `--model-override=<stage>:fable` that the user typed is its own approval, because the explicit choice of the user outranks the matrix. If the master agent picks Fable on its **own** initiative, then with `--interactive`, ask the user first, every time. Without `--interactive`, do not ask. Use Opus, and name the stage in the final report (see "Autonomy"). Both rules follow the "Model selection" section of `dev-essentials:subagent-orchestration`.

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
| Step 10: worktree removal | Only after the PR merges, or on a request of the user | Same | Same |

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

These three safeguards apply to every stage. A stage subagent never sees this file. So "Stage Launch" step 4 copies the three safeguards into the prompt of each stage, and the subagents MUST follow them too.

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

- `finalization` mode (default): each stage stages only its own changes with an explicit `git add <path>`, never `-A` or `.`. It does not commit. Stage 9 creates the one commit of the run. Then the master agent pushes and opens the PR (Step 9).
- `per-step` mode: each of the four earlier stages commits its own changes as soon as they are green. Each stage file states its own commit granularity. Stage 9 creates no commit. If `git status` shows uncommitted or unstaged source changes at the start of Stage 9, Stage 9 stops and reports. It does not commit them.

In both modes, only the master agent pushes, at Step 9 after Stage 9, never between commits. Never commit anything under `{ARTIFACTS_DIR}/`.

State `{COMMIT_MODE}` explicitly in the prompt of each commit-capable stage. Do not expect a subagent to infer it. Each commit-capable stage also gets the `<commit-conventions>` block. The block and its rules are in [references/commit-conventions.md](references/commit-conventions.md).

## Stage Launch

Before you launch a stage, do these steps in order:

1. Make sure that each file in the "Reads" column of the Overview table exists. If a file is missing, stop and name the missing files. This matters most after a `--start-from` that skipped earlier stages. One exception: if `--skip` removed the `review` stage from the plan, `review.md` is not required. Launch the stage without it.
2. Resolve the model. If this invocation has a `--model-override` entry for this stage, use it. Else use the entry of this stage in `models` of `pipeline-state.json`, from an earlier run. Else use the default model of the Overview table. Write the result into `models` (`{"<stage>": "<model>"}`). If an override of this invocation replaces a recorded entry, log the change. Pass the model in the `model` parameter of the `Agent` tool.
3. For a commit-capable stage, write the output of `git rev-parse HEAD` into `stageStartSha` (`{"<stage>": "<sha>"}`). This records the branch tip at the start of the stage. A later resume uses it to find out whether HEAD moved while the stage was incomplete.
4. Compose the prompt. Put these blocks above the text of the stage file, in this order. Every stage gets `<pipeline-discipline>` and `<worktree>`. `<clarifications>` goes only to a new launch of Stage 1 or 2 after questions (see "Stage questions"). `<commit-conventions>` goes only to the five commit-capable stages.

   ```md
   <project-context>
   {resolved project context}
   </project-context>

   <task-context>
   {contents of {ARTIFACTS_DIR}/{TASK_ID}/task-context.md}
   </task-context>

   <pipeline-discipline>
   {the text of Safeguards 1, 2, and 3 from "Pipeline Discipline", word for word}
   </pipeline-discipline>

   <worktree>
   The project root is `{WORKTREE_PATH}`. Run every git command as `git -C "{WORKTREE_PATH}" ...`. Start every other shell command (build, test, lint, coverage, migration, push, PR) with `cd "{WORKTREE_PATH}" && `, because `cd` does not persist between Bash calls. Use absolute paths under `{WORKTREE_PATH}` for each Read, Edit, and Write.
   </worktree>

   <clarifications>
   {each question of the stage, and its answer}
   </clarifications>

   <commit-conventions>
   {the block from references/commit-conventions.md, with its cadence line for {COMMIT_MODE}}
   </commit-conventions>

   {text of the stage file}
   ```

5. Replace the four placeholders in the composed prompt, also in the `<worktree>` block:
   - `{TASK_ID}`: the task ID.
   - `{WORKTREE_PATH}`: the absolute path of the project root. This is the worktree path, or the current working directory with `--no-worktree`.
   - `{ARTIFACTS_DIR}`: the repository-relative folder for the pipeline artifacts, for example `tasks` or `Notes/Tasks`.
   - `{COMMIT_MODE}`: the resolved commit cadence, `per-step` or `finalization`.
6. Make sure that no placeholder is left as a literal string in the composed prompt. `{CADENCE_LINE}` must also be gone. If one is left, stop, and name the placeholder and the stage.

After each stage, run the output check (see "Output Validation"). Then update the checkpoint (see "Checkpoints").

Read the final reply of each stage before the output check. A stage can report a STOP, a blocker, or an escalation. Examples are a blocked `implementation`, earlier test failures, and `[Ignore]` tests for implementation bugs. If it does, do not add the stage to `completed`. Handle it as a question that blocks the work ("Autonomy"): ask the user in every mode, then run the stage again or stop.

The master agent writes `review-feedback.md` before it runs `implementation` again (Build Gate, or a fix round of Human Approve #2). If the file exists, the implementation stage knows that the run is a re-entry. When the re-entry run returns, delete the file. This includes a failed run. If a retry follows, write the file again before the retry. A file that stays sends a later normal run of `implementation` to the re-entry phase, for example after `--start-from=implementation`.

### Stage questions

Stages 1 and 2 can end with a final reply that starts with the line `QUESTIONS:`. Such a run writes no file. A subagent has no `AskUserQuestion` tool, so the stage returns its questions to you. Then do these steps:

1. Do not run the output check, and do not update the checkpoint.
2. Without `--autonomous`, ask the user the questions with `AskUserQuestion`, at most 4 questions in each call.
3. With `--autonomous`, do not ask. For each question, take the option that the stage recommends. If a question has no recommended option, decide it as "Autonomy" says for a critical decision. List each answer that you picked in the final report under "Decisions for your review". Answer at most 2 rounds of questions in each stage. If the stage returns questions after the second round, stop the run, and report the open questions to the user. This step overrides the rule of "Autonomy" that a question that blocks the work stops the run in every mode.
4. Launch the stage again. Its prompt gets a `<clarifications>` block with each question and its answer. Include the questions and answers of the earlier rounds of the same stage.

## Output Validation

After each stage, and before you update the checkpoint, check the files that the stage wrote. This finds structural problems before later stages read bad input.

| File | Required headings |
| --- | --- |
| `requirements.md` | `## 1. Task Summary`, `## 2. Scope`, `## 3. Acceptance Criteria`, `## 4. Technical Constraints`, `## 5. Open Questions & Recommendations`, `## 6. Risks & Considerations` |
| `spec.md` | `## 1. Resolved Questions`, `## 2. Architecture Overview`, `## 3. Implementation Steps`, `## 4. Execution Order`, `## 6. Edge Cases & Error Handling` |
| `test-plan.md` | `## 1. Test Strategy Overview`, `## 2. Test Cases`, `## 3. Tests for Existing Code (regression)`, `## 4. Coverage Expectations` |
| `review.md` | `## Blocking Issues`, `## Warnings`, `## Suggestions`, `## Summary` |
| `security-review.md` | `## Blocking Issues`, `## Warnings`, `## Summary` |

1. Read the file after the stage is done. If the first line of `security-review.md` starts with `FETCH FAILED:`, the security stage failed to fetch the base branch. Do not check the headings, and do not run the stage again, because a rerun meets the same error. Stop the pipeline, and report the text of the file to the user.
2. Find each required heading. The match ignores case.
3. If a heading is missing, log the missing headings. Run the same stage again with this feedback: "Your output is missing required sections: [list]. Rewrite the file with all required sections." The `review` stage writes no file. For that stage, use this feedback: "Your reply is missing required sections: [list]. Return your full reply again with all required sections." Then save the new reply over `review.md`, and check it again.
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
- If Step 9 will run and `taskComments.preFinalizationPostedAt` is missing, show Human Approve #2 first, also on a resume. "Autonomy" says how the gate works in the mode of this invocation. Then post Task Comment #2. If the field is set, run neither.
- If Step 4 or a later stage will run and `buildGate.result` is not `pass` or `pass-after-retry`, run the Build Gate first.
- When you remove a stage from `completed`, remove its `stageStartSha` entry in the same write.

## Orchestration

After a compaction, Claude Code keeps only the first part of this file. If a step below is no longer in your context, read this `SKILL.md` again from the skill folder before you do the step.

### Step 0: Setup

Read [references/setup.md](references/setup.md), and do its sub-steps 1 to 15. They parse the arguments, load the project context, fetch the task, and set up the worktree. They also write `task-context.md`, load or create `pipeline-state.json` with the resume checks, and resolve `{COMMIT_MODE}`. With `--dry-run`, Step 0 creates and writes nothing, and the run ends after Step 0.

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

The master agent runs this gate. It gives the build to the agent type `dev-essentials:test-runner`, and reads only its report. The gate is not a stage, so `--model-override` does not apply to it.

1. Dispatch `dev-essentials:test-runner` with the absolute path `{WORKTREE_PATH}` and the words "build only". Also give it the build command from the project context, for example the `dotnet build ...` line under Commands.
2. If the status is GREEN, update the checkpoint, and continue with Step 4.
3. If the status is RED:
   - Write the error lines of the report (at most 50) to `{ARTIFACTS_DIR}/{TASK_ID}/review-feedback.md`, with an instruction to fix the compilation only: no new features and no refactoring.
   - Run the implementation stage again. It finds the feedback file.
   - Dispatch the test runner again with the same brief.
   - If the build fails after 2 attempts in total, stop the pipeline, and report the build errors to the user. Do not continue to `test-coverage` with broken code.
4. Record the result of the gate (`pass`, `pass-after-retry`, or `fail`) in `buildGate` of `pipeline-state.json`.

The gate keeps the test-coverage agent from spending its whole budget on compile errors.

### Steps 4 and 5: Test Coverage and Code Simplifier

Launch the stage `test-coverage`, then the stage `simplifier`. The simplifier is a plugin agent with its own simplification logic. Its stage file only adds the scope and the test rules of the pipeline.

### Steps 6, 7, and 8: Docs, Code Review, and Security Review (parallel)

Launch the stages `docs`, `review`, and `security-review` at the same time, with three `Agent` calls in one message. The reviewer is a plugin agent with its own review logic. Its stage file only adds the context and the output format. The reviewer agent has no tool that writes a file or runs git. So before its "Stage Launch" steps, run `git -C "{WORKTREE_PATH}" fetch origin <base-branch>`. Then write the diff of the task to `{ARTIFACTS_DIR}/{TASK_ID}/review-diff.patch` with `git -C "{WORKTREE_PATH}" diff --merge-base origin/<base-branch>`. Take `<base-branch>` from the project context. If the fetch fails, stop and ask the user. Do not fall back to the local `<base-branch>`, because it can be missing or stale. When the reviewer is done, write its final reply to `{ARTIFACTS_DIR}/{TASK_ID}/review.md` without a change. Then run the output check on that file. The security stage file holds its full method. Wait until all three are done, then update the checkpoint.

### Human Approve #2 (after Review)

This gate stops without `--autonomous`, because it approves the posts to the task provider, the push, and the PR of Step 9. With `--autonomous`, write the gate content to the final report, and continue to Task Comment #2. If Task Comment #1 is not posted yet, post it first. One exception: if blocking issues remain after the automatic fix round, stop and show this gate in every mode. The run cannot fix them itself. Without `--interactive`, and with blocking issues in the reviews, run one automatic fix round (the numbered steps below) before you show this gate. If the reviews still have blocking issues after that round, show this gate with the open blocking issues. If the user asks for a fix round (request changes), start one.

"Blocking issues in the reviews" means the items under `## Blocking Issues` in `review.md` and in `security-review.md`.

Show the user:

- The contents of `{ARTIFACTS_DIR}/{TASK_ID}/review.md`
- The contents of `{ARTIFACTS_DIR}/{TASK_ID}/security-review.md`
- A summary of the git diff: the changed files and the added and removed lines

If the run skipped `review` or `security-review`, show "skipped" in place of its file. The blocking issues then come only from the review file that exists.

Then ask this question: "Approve finalization (task comments, push, PR)? (yes / request changes)".

The anti-bypass clause of Human Approve #1 applies to this gate too, with the same lists of phrases that count and do not count.

Before you run `implementation` again for review findings, apply Safeguard 2 to each finding. This matters most for schema and manifest errors and for claims about library APIs.

If the reviews have blocking issues, run a fix round in these cases:

- The run has no `--interactive`, and `autoFixRound` in `pipeline-state.json` is not `true`.
- The user asks for a fix round (request changes).

Fix round steps:

1. Remove these stages from `completed` in `pipeline-state.json`: `implementation`, `test-coverage`, `simplifier`, `docs`, `review`, `security-review`, and `finalization`. In the same write, set `"autoFixRound": true`. A missing key means `false`.
2. Write the blocking issues of both reviews to `{ARTIFACTS_DIR}/{TASK_ID}/review-feedback.md`. Then run the implementation stage again with this feedback (up to 1 retry).
3. Run the Build Gate.
4. Run Step 4 (Test Coverage) again.
5. Run Step 5 (Code Simplifier) again.
6. Run Steps 6, 7, and 8 again, in parallel.
7. Go back to Human Approve #2 with the fresh review files. Show the gate even with open blocking issues.

If the user approves, continue.

### Task Comment #2 (before Finalization)

Before you launch Step 9, post a second comment. It follows the rules of Task Comment #1 and summarizes:

- What the run implemented
- The added or updated tests, and the latest test status
- Any documentation updates
- The results of the code review and the security review, or a note that the run skipped one of them
- That the task moves into finalization next
- A footer line: "This comment was generated by Claude Code"

### Step 9: Finalization + PR

Launch the stage `finalization`. It makes the commit and reports the facts for the push and the PR. It does not push. Then run the push and the PR yourself, in the main session. A push stays with the main agent (`dev-essentials:subagent-orchestration` Rule 4), so that the user sees the push command and its result. Human Approve #2 approved both, or `--autonomous` did.

1. Push. If the report gives no push command, say so in the final report, and do not invent a push step. If the current branch is the default branch of the repository, do not push. Stop and report it. Else run `cd "{WORKTREE_PATH}" && <push command>`. Never force-push, and never pass `--no-verify`. If the push fails because the history diverged, stop and report it.
2. Create the PR. If the report gives no PR command, skip this step. Report the branch status and the work that is left for the human. If the PR command is a shell command, run `cd "{WORKTREE_PATH}" && <PR command>`. If it is an MCP tool name, load the tool with `ToolSearch`. Then call it with the base branch, the title, and the body of the report.
3. If the report names a linking tool, link the PR to its tracking issue. Load the tool with `ToolSearch`, and create the link. If the link fails, report the failure, and continue, because the PR exists. Without a linking tool, the task URL in the PR body is the link.
4. If step 1 or step 2 fails, stop and report the failure. Do not try workarounds.

Add `finalization` to `completed` only after these steps. Then update the checkpoint, and report the branch or PR status.

If the run created a PR, write its `number`, `url`, `owner`, and `repo` into `pr` of `pipeline-state.json` before Step 10. If it created no PR (a branch-only flow, or no PR command), leave `pr` as `null`. Step 10 reads this field to decide whether it needs a GitHub PR lookup.

### Step 10: Cleanup

After the result of Step 9 is final, read [references/cleanup.md](references/cleanup.md), and do its steps. Do not archive the task logs or remove the worktree before you read it. By default, the worktree and the artifacts stay until the PR is merged.
