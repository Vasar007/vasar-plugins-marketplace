# Stage launch

The master agent reads this file before the first stage launch of a run. It has the files of each stage, the launch steps, and the steps after a stage. It also has the second launch of a stage: the Build Gate retry, the fix round, and the stage questions. The output check is last.

## Contents

- Stage files
- Launch steps
- Review patch
- After the stage
- Re-entry of the implementation stage
- Build Gate retry
- Fix round
- Stage questions
- Output Validation

## Stage files

Each stage reads and writes files in `{ARTIFACTS_DIR}/{TASK_ID}/`. Every stage also gets the task context (`task-context.md`, injected).

| # | Stage key | Reads | Writes |
| --- | --- | --- | --- |
| 1 | `requirements` | Task context only | `requirements.md` |
| 2 | `spec` | `requirements.md` | `spec.md`, `test-plan.md` |
| 2b | `plan-artifact` | `requirements.md`, `spec.md`, `test-plan.md` | `{TASK_ID}-implementation-plan.html` |
| 3 | `implementation` | `requirements.md`, `spec.md`, `test-plan.md`, and `review-feedback.md` on a re-entry | Code and tests |
| 4 | `test-coverage` | `requirements.md`, `spec.md`, `test-plan.md` | Test files |
| 5 | `simplifier` | The diff against the base branch | Code |
| 6 | `docs` | `requirements.md`, `spec.md` | Docs |
| 7 | `review` | `requirements.md`, `spec.md`, `test-plan.md`, `review-diff.patch` | Final reply, which the master agent saves as `review.md` |
| 8 | `security-review` | `requirements.md`, `spec.md`, `review-diff.patch` | `security-review.md` |
| 9 | `finalization` (the master agent) | `requirements.md`, `spec.md`, `review.md` | Commit, push, and PR |

## Launch steps

Before you launch a stage, do these steps in order:

1. Make sure that each file in the "Reads" column of "Stage files" exists. If a file is missing, stop and name the missing files. This matters most after a `--start-from` that skipped earlier stages. One exception: if `--skip` removed the `review` stage from the plan, `review.md` is not required. Launch the stage without it.
2. Resolve the model. If this invocation has a `--model-override` entry for this stage, use it. Else use the entry of this stage in `models` of `pipeline-state.json`, from an earlier run. Else use the default model of the Overview table in `SKILL.md`. Write the result into `models` (`{"<stage>": "<model>"}`). If an override of this invocation replaces a recorded entry, log the change. Pass the model in the `model` parameter of the `Agent` tool.
3. For a commit-capable stage, write the output of `git rev-parse HEAD` into `stageStartSha` (`{"<stage>": "<sha>"}`). This records the branch tip at the start of the stage. A later resume uses it to find out whether HEAD moved while the stage was incomplete.
4. Compose the prompt. Put these blocks above the text of the stage file, in this order. Every stage gets `<pipeline-discipline>` and `<worktree>`. `<clarifications>` goes only to a new launch of Stage 1 or 2 after questions (see "Stage questions"). `<commit-conventions>` goes only to Stages 3 to 6, the commit-capable stages that run in a subagent. `<start-changes>` goes to the same stages. If `startChanges` is empty, leave it out.

   ```md
   <project-context>
   {resolved project context}
   </project-context>

   <task-context>
   {contents of {ARTIFACTS_DIR}/{TASK_ID}/task-context.md}
   </task-context>

   <pipeline-discipline>
   {the text of Safeguards 1, 2, and 3 from references/pipeline-discipline.md, word for word}
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

   <start-changes>
   These paths had changes before this run started. Do not stage them, and do not commit them, unless your stage edits that path. If your stage edits one, name it in your final reply.
   {the paths of startChanges, one for each line}
   </start-changes>

   {text of the stage file}
   ```

5. Replace the placeholders in the composed prompt, also in the `<worktree>` block:
   - `{TASK_ID}`: the task ID.
   - `{WORKTREE_PATH}`: the absolute path of the project root. This is the worktree path, or the current working directory with `--no-worktree`.
   - `{ARTIFACTS_DIR}`: the repository-relative folder for the pipeline artifacts, for example `tasks` or `.pipeline`.
   - `{COMMIT_MODE}`: the resolved commit cadence, `per-step` or `finalization`.
6. Make sure that no placeholder is left as a literal string in the composed prompt. `{CADENCE_LINE}` must also be gone. If one is left, stop, and name the placeholder and the stage.

## Review patch

The review stage writes no file. It runs no git command that changes state. The review and the security review read one fixed patch. So before the launch steps of Stage 7 and Stage 8, run `git -C "{WORKTREE_PATH}" fetch origin <base-branch>`. Then write the diff of the task to `{ARTIFACTS_DIR}/{TASK_ID}/review-diff.patch` with `git -C "{WORKTREE_PATH}" diff --merge-base origin/<base-branch> -- . ':(exclude,literal)<path>'`. The user changed the paths of `startChanges` before the run. Add one `':(exclude,literal)<path>'` for each of them that no stage edited. "After the stage" notes the edited paths. If the edited paths are unknown (see "After the stage"), exclude every path of `startChanges`, except a path for which `git -C "{WORKTREE_PATH}" log --oneline origin/<base-branch>..HEAD -- <path>` prints a commit. If `startChanges` is empty, leave out the pathspec. Take `<base-branch>` from the project context. If the fetch fails, stop and ask the user. Do not fall back to the local `<base-branch>`, because it can be missing or stale. When the review is done, write its final reply to `{ARTIFACTS_DIR}/{TASK_ID}/review.md` without a change. Then run the output check on that file.

## After the stage

A final reply of Stage 1 or Stage 2 can start with the line `QUESTIONS:`. Then do the steps of "Stage questions" instead of the steps below.

Read the final reply of each stage before the output check. A stage can report a stop, a blocker, or an escalation. Examples are a blocked `implementation`, earlier test failures, and `[Ignore]` tests for implementation bugs. If it does, do not add the stage to `completed`. Handle it as a question that blocks the work (hard stop 6 of `dev-essentials:work-modes`): ask the user in every mode, then run the stage again or stop.

If the final reply of a commit-capable stage names a path of `startChanges` that the stage edited, note the path. Use the noted paths at Step 9 (`stages/finalization.md`), and name them in the final report of the run. If a resume or a compaction lost these notes, use "unknown".

Then run the output check (see "Output Validation"), and update the checkpoint ("Checkpoints" in `SKILL.md`).

Stage 2b does not block the pipeline. The stage failed in these cases: its final output has no `ARTIFACT: <path>` line, or the named file does not exist. If it failed, run it once more. If it fails again, log a warning, and continue without the artifact. Add `plan-artifact` to `completed` after each of these outcomes: success, success at the retry, or give-up. Then a resume does not try a broken render again. Also record `planArtifact` (see the schema in `references/checkpoint-protocol.md`).

## Re-entry of the implementation stage

The master agent writes `review-feedback.md` before it runs `implementation` again (Build Gate, or a fix round of Human Approve #2). If the file exists, the implementation stage knows that the run is a re-entry. When the re-entry run returns, delete the file. This includes a failed run. If a retry follows, write the file again before the retry. A file that stays sends a later normal run of `implementation` to the re-entry phase, for example after `--start-from=implementation`.

## Build Gate retry

If the status of the Build Gate is RED:

1. Write the error lines of the build (at most 50) to `{ARTIFACTS_DIR}/{TASK_ID}/review-feedback.md`, with an instruction to fix the compilation only: no new features and no refactoring.
2. Run the implementation stage again. It finds the feedback file.
3. Run the build of the gate again, with the same command and filter.

The limit of 2 attempts and the stop are in "Build Gate" in `SKILL.md`.

## Fix round

Before you run `implementation` again for review findings, apply Safeguard 2 of `references/pipeline-discipline.md` to each finding. This matters most for schema and manifest errors and for claims about library APIs.

1. Remove these stages from `completed` in `pipeline-state.json`: `implementation`, `test-coverage`, `simplifier`, `docs`, `review`, `security-review`, and `finalization`. In the same write, set `"autoFixRound": true`. A missing key means `false`.
2. Write the blocking issues of both reviews to `{ARTIFACTS_DIR}/{TASK_ID}/review-feedback.md`. Then run the implementation stage again with this feedback (up to 1 retry).
3. Run the Build Gate.
4. Run Step 4 (Test Coverage) again.
5. Run Step 5 (Code Simplifier) again.
6. Run Steps 6, 7, and 8 again, in parallel.
7. Go back to Human Approve #2 with the fresh review files. Show the gate even with open blocking issues.

## Stage questions

Stages 1 and 2 can end with a final reply that starts with the line `QUESTIONS:`. Such a run writes no file. A subagent has no `AskUserQuestion` tool, so the stage returns its questions to you. Then do these steps:

1. Do not run the output check, and do not update the checkpoint.
2. Outside the full mode, ask the user the questions with `AskUserQuestion`, at most 4 questions in each call.
3. In the full mode, do not ask. For each question, take the option that the stage recommends. If a question has no recommended option, decide it as `dev-essentials:work-modes` says for a critical decision. List each answer that you picked in the final report under "Decisions for your review". Answer at most 2 rounds of questions in each stage. If the stage returns questions after the second round, stop the run, and report the open questions to the user. This step overrides the hard stop of `dev-essentials:work-modes` for a question that blocks the work.
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
