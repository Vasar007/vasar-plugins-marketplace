# Checkpoint protocol

The master agent reads this file at Step 0 of `SKILL.md`. It has the schema of `pipeline-state.json`, the notes for each field, and the validation of the file. It also has the rules for the updates during the run and the two resume checks.

## Contents

- Schema
- Field notes
- Validation of the state file
- Updates during the run
- Interruption check (resume)
- Mode-change check (`per-step` to `finalization`)

## Schema

The master agent keeps `{ARTIFACTS_DIR}/{TASK_ID}/pipeline-state.json` up to date during the whole run.

```json
{
  "taskId": "TASK-123",
  "taskSource": "provider",
  "worktree": "feature/task-123",
  "noWorktree": false,
  "stage": "implementation",
  "completed": ["requirements", "spec"],
  "taskComments": {
    "analysisPostedAt": null,
    "analysisCommentId": null,
    "preFinalizationPostedAt": null,
    "preFinalizationCommentId": null
  },
  "buildGate": {
    "result": null,
    "attempts": 0
  },
  "pr": null,
  "models": {},
  "stageStartSha": {},
  "planArtifact": null,
  "commitMode": "finalization",
  "startChanges": [],
  "failed": null,
  "startedAt": "2026-03-01T11:00:00Z",
  "updatedAt": "2026-03-01T11:30:00Z"
}
```

All state files of a task are in `{ARTIFACTS_DIR}/{TASK_ID}/`, for example `{ARTIFACTS_DIR}/TASK-123/`. So more than one task can use the same worktree without conflicts.

## Field notes

- `taskSource` is `"provider"` for a task ID and `"request"` for a plain request. Step 0 sets it (sub-step 2 of `references/setup.md`). A resume never changes it.
- `pr` is `null` until Step 9 is done. If Step 9 creates a PR, the field gets `{ "number": <int>, "url": "<string>", "owner": "<string>", "repo": "<string>" }`. In a branch-only flow (no PR), `pr` stays `null`. Step 10 uses this field to decide whether it needs a GitHub PR status lookup before the archive gate and the worktree-removal gate.
- `models` starts as `{}`. It gets one entry (`"<stage>": "<model>"`) for each stage that a subagent runs. `finalization` gets none, because the master agent runs it. The entry appears at the time that the model of the stage is resolved (step 2 of "Launch steps" in `references/stage-launch.md`). A resumed run reads it back and keeps the same models. Only a fresh `--model-override` overwrites an entry.
- `stageStartSha` starts as `{}`. It gets one entry (`"<stage>": "<sha>"`) for each commit-capable stage at its launch: the output of `git rev-parse HEAD` at that time (step 3 of "Launch steps"). It grows in the same way as `models`. It is the only input of the interruption check below.
- `planArtifact` is `null` until Stage 2b runs. It then gets `{ "path": "<repo-relative path>", "status": "rendered" | "failed" | "skipped" }`. The status values:
  - `"rendered"`: the stage wrote the HTML artifact (after 0 or 1 retries).
  - `"failed"`: both attempts failed.
  - `"skipped"`: the run skipped the stage, for example with `--skip=plan-artifact`.
- `commitMode` is `"finalization"` by default. With `--commit-mode=per-step` at Step 0, it is `"per-step"`. Each checkpoint write keeps it, so that a resumed run uses the original choice. Two cases change it: a new `--commit-mode` on that invocation, or the mode-change check below (see also "Commit Cadence" in `SKILL.md`).
- `startChanges` is `[]` in a new worktree. Else Step 0 writes the paths that `git status --porcelain` listed before the run (sub-step 6 of `references/setup.md`). A resume keeps the recorded list. Stage Launch passes it to the five commit-capable stages.
- `autoFixRound` is not in the schema above. The first fix round of Human Approve #2 sets it to `true`. A missing key means `false`.

## Validation of the state file

Do these checks on each write, and on each load at a resume:

- Parse the file as JSON. If it is not valid JSON, stop at once.
- Find out whether each top-level key of the schema above exists (17 keys). For a missing key of the backward-compatibility table below, use its zero value. For any other missing key, stop and report it.
- Backward compatibility: an old state file can lack `taskSource`, `pr`, `models`, `stageStartSha`, `planArtifact`, `commitMode`, or `startChanges`. On a read, each missing key takes the zero value in the table below. The next write stores it.

  | Field | Zero value |
  | --- | --- |
  | `taskSource` | `"provider"` |
  | `pr` | `null` |
  | `models` | `{}` |
  | `stageStartSha` | `{}` |
  | `planArtifact` | `null` |
  | `commitMode` | `"finalization"` |
  | `startChanges` | `[]` |

  Each key is still required on each write. The zero values apply to reads only. Step 9 fills `pr` at the next PR creation. Step 10 treats `null` as the case without a PR.
- Find out whether `completed` is an array of known stage names. If it is not, stop and report it.
- Find out whether `stage` is a known stage name or `null`. If it is not, stop and report it.

## Updates during the run

- After each successful stage, update `stage` and `completed`. After each posted task comment, update `taskComments`.
- On a resume, start at the first stage that is not in `completed`. `--start-from=<stage>` overrides this resume point. `--skip=<stage>` removes the stage from the plan.
- If an earlier stage runs again and it can change code or docs, first remove all later dependent stages from `completed`.
- If `spec` runs again, also remove `plan-artifact` from `completed`, so that the HTML artifact renders again from the new spec.
- If `requirements` or `spec` runs again, clear both task-comment checkpoints, so that both comments post fresh summaries.
- If a code, test, docs, review, or security stage runs again after Task Comment #2 was posted, clear only the checkpoint of Task Comment #2.
- If `taskSource` is `provider`, and Step 3 or a later stage will run, and `taskComments.analysisPostedAt` is missing, post Task Comment #1 first. In the default mode, Human Approve #2 posts it instead.
- If Step 9 will run and `taskComments.preFinalizationPostedAt` is missing, show Human Approve #2 first, also on a resume. If Human Approve #2 already passed in this session, do not show it again. "Autonomy" in `SKILL.md` says how the gate works in the mode of this invocation. A request run never sets this field, so a resumed request run always shows the gate again.
- If `taskSource` is `provider`, and Step 9 will run, and `taskComments.preFinalizationPostedAt` is missing, post Task Comment #2 after Human Approve #2. If the field is set, the gate and the comment are done, so run neither.
- If Step 4 or a later stage will run and `buildGate.result` is not `pass` or `pass-after-retry`, run the Build Gate first.
- When you remove a stage from `completed`, remove its `stageStartSha` entry in the same write.

## Interruption check (resume)

Checkpoints record whole stages only. `completed` holds stage names, with no progress inside a stage. So before you resume a commit-capable stage, find out whether it ran in part.

The commit-capable stages are `implementation`, `test-coverage`, `simplifier`, `docs`, and `finalization`. For each of them that is not in `completed` and has a `stageStartSha` entry, compare `git rev-parse HEAD` with the `stageStartSha` entry of that stage. If they differ, stop and report. Do not restart that stage from scratch. A restart can make duplicate or conflicting commits for work that is already committed. It can also start a Stage 9 that wrongly expects a clean tree.

The check does not depend on `{COMMIT_MODE}`. It finds a `per-step` stage that stopped after some of its own commits. It also finds a Stage 9 in `finalization` mode that stopped after the commits of other stages landed. HEAD moved in both cases.

- Order: the check runs right after the load of `pipeline-state.json` (Step 0, sub-step 11). It runs before sub-step 12 resolves `{COMMIT_MODE}` and overwrites the recorded value. It uses only `stageStartSha` and `completed`, never `{COMMIT_MODE}`. So a resume cannot escape it with a new `--commit-mode` value.
- With `--dry-run`, report the result in the announced plan, but do not stop. A dry run never touches the branch, so it has nothing to protect.
- There are two allowed ways past this stop. Only the first one works with `--start-from` alone.
  1. Discard the extra commits. Reset HEAD to the recorded `stageStartSha` of the stage. Then resume with `--start-from=<stage>`, with the interrupted stage or a later one. That flag overrides the checkpoint resume point. HEAD now matches the recorded SHA, so the check passes.
  2. Keep the extra commits. `--start-from` alone changes neither `stageStartSha` nor `completed`, so the stop fires again on the next invocation. So first update the state by hand. Add the interrupted stage to `completed` in `pipeline-state.json`, or set its `stageStartSha` entry to the new HEAD. Then resume with `--start-from=<stage>`. If the interrupted stage is `finalization` and HEAD is its own commit, set `stageStartSha`, and do not add the stage to `completed`. A stage in `completed` skips the push and the PR.

  Do not resume past this stop in any other way.

## Mode-change check (`per-step` to `finalization`)

This check covers the one gap that the interruption check cannot see. The interruption check compares HEAD with `stageStartSha`. But in `finalization` mode, stages only stage their changes and never commit, so HEAD does not move during them. Without this check, a resume that changes the mode from `per-step` to `finalization` keeps the earlier `per-step` commits on the branch. The new finalization run then adds one more commit at the end. That breaks the promise of one commit for the whole run ("Commit Cadence" in `SKILL.md`).

If all three conditions below are true, stop and report before you overwrite `commitMode`.

- The resolved `{COMMIT_MODE}` is `finalization`.
- The recorded `commitMode`, before the overwrite of this resume, is `per-step`.
- At least one commit-capable stage is already in `completed`. It can have made commits in the old `per-step` mode.

Do not accept the new mode silently.

The reverse change, `finalization` to `per-step`, needs no check of its own in the common case. If no commit-capable stage runs between the resume point and Stage 9, Stage 9 itself stops on any uncommitted or unstaged change ("Commit Cadence"). A commit-capable stage that runs in between commits only its own paths ("Commit with paths" in `references/commit-conventions.md`). So the changes that the earlier `finalization` stages staged stay staged, and Stage 9 stops on them. This protocol adds no check for that case.

All other resume cases keep the log-and-allow rule of sub-step 12:

- `per-step` to `per-step`
- `finalization` to `finalization`
- `finalization` to `per-step`
- `per-step` to `finalization`, with no commit-capable stage in `completed` yet

More rules for this check:

- Order: the check runs after sub-step 12 reads the recorded `commitMode`, and strictly before sub-step 12 writes the new value to `pipeline-state.json`. If this stop fires, write nothing to `pipeline-state.json`.
- With `--dry-run`, report the result in the announced plan, but do not stop, as for the interruption check.
- There are two allowed ways past this stop:
  1. Resume with `--commit-mode=per-step`. The run keeps the original cadence and commits per step. `pipeline-state.json` needs no change.
  2. Reset the branch to the state before the `per-step` commits, and start a fresh run in `finalization` mode. Also remove the affected commit-capable stages from `completed`, with their `stageStartSha` entries. Or delete `pipeline-state.json` for a truly fresh run. A branch reset without this state change leaves `completed` and `commitMode` pointing at the discarded commits. The stop then fires again on the next invocation. If a run goes past the stop anyway, it skips the stages that the reset undid, and it makes an empty finalization commit.

  Do not resume past this stop in any other way.
