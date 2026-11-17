# Role briefs

Fill the placeholders and paste each brief into its dispatch. Each brief is self-contained, because the agent sees only its brief.

## Contents

- Planner (read-only on the workspace)
- Reviewer (read-only, fresh context)
- Fixer

Shared placeholders:

| Placeholder | Meaning |
| --- | --- |
| `{SKILL_DIR}` | Absolute path of this skill |
| `{WORKSPACE}` | Absolute path of the tree to trim |
| `{BACKUP}` | Absolute path of the backup taken before the pass |
| `{PROTECT_SET}` | The two protect-set tiers (byte-identical and substance), in words, for this workspace |
| `{GLOB}` | One `--glob PATTERN` flag that covers every file type of the protect-set, or nothing for the default `**/*.md` |
| `{ID_REGEXES}` | One `--id-regex` flag per id family |
| `{PROTECTED_REGEXES}` | One `--protected-regex` flag per protected block type |
| `{ALLOW_FLAGS}` | One `--allow-changed REGEX` flag per tombstone, or nothing. REGEX matches `PATH:FIRST_LINE`. The planner lists its proposed tombstones. The other roles use the approved ones. |
| `{TARGETS}` | Byte targets per profile, with any user overrides |
| `{PROGRESS_DIR}` | Folder for the agent's `_`-prefixed progress file |
| `{LINT_COMMAND}` | The project's Markdown linter or formatter, or "none" |
| `{BATCH_FILES}` | Relative paths of the files in one batch |
| `{PLAN_PATH}` | Where the planner writes the plan, outside the workspace. For the reviewer: the plan path of every batch |
| `{SCRATCH}` | Scratch folder for the planner's `orig` and `target` copies, one folder for each batch |
| `{APPROVED_TOMBSTONES}` | The tombstone list that the user approved at the gate, or "none" |
| `{REVIEW_PATH}` | Where the reviewer writes its findings |
| `{FINDINGS}` | The review findings that the orchestrator accepted |
| `{ROLE}` | planner, reviewer or fixer |
| `{BATCH_ID}` | Short id of the batch, for example `b1`. For the reviewer and the fixer: `all` |

Every brief ends with the same crash-safety block:

```text
Keep {PROGRESS_DIR}/_{ROLE}-{BATCH_ID}-progress.md up to date at every step. It has a STATUS line,
a list of steps, an append-only "## Log", a "## Current draft" section, and a "## NEXT"
section with the single next action. If the file exists at start, read it and continue
from NEXT. Delete it as your last step, after your report is complete.
```

## Planner (read-only on the workspace)

```text
You plan a trim pass for one batch. Do not edit {WORKSPACE}.
Read {SKILL_DIR}/references/cut-rules.md, artifact-profiles.md and plan-template.md first.

Batch files: {BATCH_FILES}
Protect-set: {PROTECT_SET}
Targets in bytes: {TARGETS}

1. Read every file of the batch in full.
2. Classify each file with a profile. Write one plan to {PLAN_PATH} in the template format.
   List each protected item that you withdraw as a tombstone, with its file and a regex for PATH:FIRST_LINE.
3. Measure bytes, not lines. Joining lines is not a cut. Remove words.
4. If a file stays above its target, write why in the plan.
5. Prove every anchor and end quote with the anchor proof script. Each must match once.
6. Copy every file that the glob matches in {WORKSPACE}, not only the batch, with its relative paths,
   to {SCRATCH}/orig and {SCRATCH}/target. Apply the whole plan to target: each cut, each cross-file
   fix, each merge, and each deletion. The orchestrator copies target into {WORKSPACE} as it is.
   Each file that the plan changes or deletes must match the glob. If one does not, stop and report it.
7. Run: python3 -I {SKILL_DIR}/scripts/trim_report.py --before {SCRATCH}/orig
   --after {SCRATCH}/target {GLOB} {ID_REGEXES} {PROTECTED_REGEXES} {ALLOW_FLAGS}
8. If it fails, fix the plan and repeat until it passes.

Report in at most 25 lines: the plan path, the size table total, the deletion list
with one reason each, and every file above target with its reason.
```

## Reviewer (read-only, fresh context)

```text
You review a finished trim pass. Do not edit anything.
Before state: {BACKUP}. After state: {WORKSPACE}. Protect-set: {PROTECT_SET}.
Approved tombstones: {APPROVED_TOMBSTONES}
Plans: {PLAN_PATH}
Targets in bytes: {TARGETS}. Each plan names the profile of each file.

1. Run python3 -I {SKILL_DIR}/scripts/trim_report.py --before {BACKUP} --after {WORKSPACE}
   {GLOB} {ID_REGEXES} {PROTECTED_REGEXES} {ALLOW_FLAGS}. Find out whether each ALLOWED
   block is on the approved tombstone list. Report each one that is not.
   For each IN OTHER FILE line, find out whether a plan names the move or the
   deduplication. Report each one that no plan names.
   Look at each AMBIGUOUS line by hand.
   Read the lines right next to each protected block. The script does not test them.
   Report added text there that reverses a decision.
2. Sample at least 8 files across all batches. Compare key facts with the backup:
   recommendations, fallback plans, requirements, question defaults, risks,
   milestones, tool choices, sources, and uncertainty markers.
3. Test integrity: no dangling references, cross-file section citations resolve,
   paired rows exist on both sides, counts in prose match tables, process documents
   agree with each other.
4. Read rewritten text for broken sentences, "see above" leftovers, and user tags
   attached to agent text.
5. List files that are still above their target in bytes.

Severity: a lost protected item or a lost needed fact is High or Critical.
Bloat is Medium or Low.
Each blocking finding gives the file and line, why it is wrong, and how to show
that it fails (input or state, then the wrong result). If you cannot show the
failure, say so instead of asserting it.

Write the review to {REVIEW_PATH}. Report the counts per severity in at most 15 lines.
```

## Fixer

```text
You fix the accepted findings of a trim review.
Review: {REVIEW_PATH}. Accepted findings: {FINDINGS}. Backup: {BACKUP}.
Workspace: {WORKSPACE}.

1. For each finding, decide APPLY, PARTIAL or REJECT, with one line of reason.
2. Restore lost facts verbatim from the backup. Do not rephrase byte-identical text.
3. Fix only what the findings name. Do not start new cuts.
4. Run: python3 -I {SKILL_DIR}/scripts/trim_report.py --before {BACKUP}
   --after {WORKSPACE} {GLOB} {ID_REGEXES} {PROTECTED_REGEXES} {ALLOW_FLAGS}
5. Run {LINT_COMMAND} on the changed files. Fix every failure that the script or the linter reports.

Report in at most 20 lines: each finding with its decision, and the script result.
```
