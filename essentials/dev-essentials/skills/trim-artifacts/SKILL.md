---
name: trim-artifacts
description: >-
  Trim pass for text artifacts: notes, plans, research, state and handoff files,
  agent memory, logs and task lists. It removes history, review records, process residue,
  duplication and stale snapshots. It protects the user's decisions, identifiers, needed
  facts with their sources, and uncertainty markers. Use it for "trim", "compact",
  "prune", "shrink", "clean up notes", "shrink context files" or "this memory is bloated".
  Also use it for "remove history from docs", "cut the changelog noise" or "the context
  costs too many tokens". Use it to rewrite a context or handoff file that has grown a
  log. Do not use it to simplify source code. Code cleanup belongs to /simplify.
---

# Trim artifacts

A trim pass removes text that only records how a workspace reached its current state.
If a line helps a future reader decide, plan, build or answer, it stays. Other text goes.

## Terms

- Workspace: the folder tree that the pass trims.
- Orchestrator: the main agent that runs the steps and dispatches the roles.
- Protect-set: the text and ids that the pass must keep. It has two tiers.
- Byte-identical tier: declared decisions, requirements that the user declared word for word, and ids. The pass must not change one byte of them.
- Substance tier: needed facts with their sources, uncertainty markers, and all other requirements. The pass can shorten the wording. The meaning, the source and the marker must stay.
- Anchor: a short verbatim quote that marks the start of a cut. It must match its file exactly once.
- Batch: a group of files that one planner handles.
- Planner, executor, reviewer, fixer: the four roles. The planner writes the cut plan. The executor applies it. The reviewer tests the result. The fixer repairs the findings.
- Tombstone: the one-line stub that replaces a withdrawn protected item. The id stays, so that old citations still resolve.
- Deletion gate: step 5, where the user approves each file deletion and each tombstone.
- Cut table: the list of allowed cut reasons in [references/cut-rules.md](references/cut-rules.md). That file also holds the tombstone template.
- Progress file: a `_`-prefixed file where an agent records its steps, so that a crashed run can resume.
- Results file: the file where step 8 records what the pass cut.

If you are not sure, keep the fact and cut its narration. This is the tie-break rule.
The user can change these defaults: the size limits for the light path, the batch load, the pilot batch and the cap of 2 fix rounds.

## Requirements

The script needs Python 3 and only its standard library. The example commands use a POSIX shell (`cp -a`, `find`, `grep`, `sed`).

## Choose the path

- The light path is for one file or a few small files. Run it inline with no subagents. See "Light path" below.
- The full pass is for a folder tree or many files. Run the 12 steps with a separate agent for each role.

If the user did not say which, pick by size. More than about 10 files or 100 KB means a full pass.

## The algorithm (full pass)

### 1. Settle scope and the protect-set

Ask the user for the protect-set, or infer it. Before you plan, get the user's approval. The protect-set has four parts:

1. Declared decisions are text that the user declared as their decision. Keep it byte-identical. You can cut agent-written framing around it. If the user declared a requirement word for word, it is byte-identical too.
2. Identifiers are ids that other files and people cite. Detect id families by pattern, then show the list to the user. Never renumber or reuse an id.
3. Needed facts are recommendations, fallback plans, requirements, open questions with defaults, risks and chosen tools. Every requirement that the user did not declare word for word is a needed fact. Keep each fact with the source (URL and date) of each claim that it uses.
4. Uncertainty markers are labels such as "unverified" or "assumption". Without them, a guess reads as a fact.

Parts 1 and 2 form the byte-identical tier. Parts 3 and 4 form the substance tier.

Other verbatim user text is not in the protect-set. If it duplicates protected text, you can delete it. Never paraphrase it. Keep it verbatim, or remove it.

List the file types in the workspace, for example with `find WORKSPACE -type f | sed -E 's|.*/||; s/.*\.//' | sort | uniq -c`. The script checks `**/*.md` by default. If other types can cite a trimmed file, such as `.txt` or `.log`, use `--glob '**/*'` in one run. A separate run for each type cannot see a `.txt` file that cites a deleted `.md` file. Record the glob in the protect-set.

The glob `**/*` also walks hidden folders such as `.git`. In a git workspace, a deleted file then shows as DANGLING in `.git/index`. The size table also counts git objects. Instead, compare the subfolder that holds every file that can cite a trimmed file, for example `--before BACKUP/docs --after WORKSPACE/docs`. The glob and the PATH in each `--allow-changed` regex are then relative to that subfolder. The default glob `**/*.md` does not match the git index or objects, so only `**/*` has this problem.

To find id families, list the prefixes of tokens that look like ids:

```bash
grep -rhoE '\b[A-Z][A-Z0-9]*-?[0-9]+\b' --include='*.md' WORKSPACE \
  | sed -E 's/[0-9]+$//' | sort | uniq -c | sort -rn
```

Drop noise such as version strings. Turn each real family into one regex, for example `\bREQ-\d+\b`.

Then write one multiline regex for each protected block type. It must cover only the byte-identical text, such as the quote and the decision line, not the whole section. Then the pass can still cut the agent framing around a decision. Example for files with a quote line and a decision line:

```text
(?m)^## Decision \d+\n\nQuote: .*\nDecision: .*$
```

Make sure that each regex matches at least once in the workspace.

Also settle the byte targets (defaults are in [references/cut-rules.md](references/cut-rules.md)), the backup location, and who approves deletions.

### 2. Back up the workspace

Before the first edit, copy the whole workspace to a location outside it, for example with `cp -a WORKSPACE BACKUP`.
The script refuses a `--before` path that equals, contains, or sits inside the `--after` path. It cannot see a stray copy that you do not pass to it. It also cannot see a backup inside the workspace in the subfolder form. Keep every copy outside the workspace, because a copy inside it can hide a loss.
Then tell the user the path and the size of the backup in one short sentence. For example, get the size with `du -sh BACKUP`.
If a second backup exists, list every backup in that sentence.
Record the path and the size in the progress file and the results file.
If you run a second pass, first take a second backup.
Deleting a backup is the last step, and it needs the user's approval.

### 3. Batch the files

Group files by folder or by artifact type. Give each planner a load that it can read in full: 20 to 40 files or about 300 KB.
Classify each file with a profile from [references/artifact-profiles.md](references/artifact-profiles.md). The profile sets its keep rules, cut rules and target.

### 4. Plan each batch (read-only)

The planner reads every file of its batch and writes one plan per batch. Use [references/plan-template.md](references/plan-template.md). Per file, the plan gives:

- The action: keep, trim, delete, or merge into another file.
- Bytes now, and bytes expected after.
- Each cut with its anchor, its operation and a reason from the cut table.
- Cross-file fixes for every reference that a deletion or a move breaks, and corrected counts.
- Each tombstone with its file and a regex for `PATH:FIRST_LINE` (see step 7).

The planner proves each anchor with a script. Then it makes two copies of the batch in a scratch folder, an `orig` copy and a `target` copy. Each copy keeps the relative paths, so that a regex with a path still matches. It applies the plan to `target` and runs `scripts/trim_report.py` against `orig`, with one `--allow-changed` for each proposed tombstone. This is the dry run.
Keep plans and scratch copies outside the workspace, so that the pass does not measure or trim them.

Measure bytes, not lines. Agents pay for bytes. Joining lines is not a cut: it drops the line count and keeps the cost. Remove words instead. If a file stays above its target, the plan says why.

### 5. Gate the deletions

Before any deletion, show the user these lists:

1. The files to delete, with a one-line reason each.
2. Files or records that the user approved for deletion before the pass, to show the real scope.
3. The protected items that the plan withdraws as tombstones, each with its file and its `--allow-changed` regex.

Under the lists, add one line that reminds the user of the path of the backup.

Deletions and tombstones are destructive. Wait for explicit approval of each item. If the user rejects an item, the planner removes it from the plan and reruns the dry run.
For a large workspace, first run one pilot batch, a small batch that tests the targets. Show its size table.

### 6. Apply the plan exactly (executor)

1. Make sure that each workspace file is byte-identical to the planner's `orig` copy. If not, stop and report.
2. Apply each cut by its anchor. Delete the planned files. Remove folders that the deletions emptied.
3. Compare the result with the planner's `target` copy, for example with `diff -r`.
4. Report every place where the plan did not apply as written.

Do not cut more than the plan says.
If a removal changes the meaning of protected content, do not edit. Report it instead.

### 7. Measure and test with the script

Run [scripts/trim_report.py](scripts/trim_report.py) against the backup. The folder of this skill is `${CLAUDE_SKILL_DIR}`. In the reference files, `{SKILL_DIR}` stands for this folder:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/trim_report.py" --before BACKUP --after WORKSPACE \
  --id-regex '\bREQ-\d+\b' \
  --protected-regex '(?m)^## Decision \d+\n\nQuote: .*\nDecision: .*$' \
  --allow-changed '^notes/decisions\.md:## Decision 3\b' --target-percent 60
```

- Exit code 0 means pass. Exit code 1 means an integrity failure. Exit code 2 means a usage error. Examples are a bad flag, an unreadable path, an absolute `--glob` and a backup inside the workspace.
- A regex that matches nothing in the backup is a failure.
- The script converts CRLF to LF in both trees before it matches or compares.
- A glob is one relative pattern from the root of the tree. `*.md` matches only top-level files. `notes/*.md` matches only files in `notes/`. `**/*.md` matches files at any depth.
- A protected block is exactly the text that its regex matches. Text that you add after the match, such as an `Update:` line below the decision line, is not tested.
- For each approved tombstone, add `--allow-changed REGEX`. The script tests REGEX against the string `PATH:FIRST_LINE`. PATH is the relative path with forward slashes. FIRST_LINE is the first line of the protected block.
- To allow a block in one file, write the file in the regex, for example `'^notes/decisions\.md:## DEC-3\b'`. To allow it in any file, write `':## DEC-3\b'`.
- The script reports a matching block as ALLOWED. After the trim, the same file must still hold a line that matches REGEX. If not, the script reports WITHDRAWN, NO TOMBSTONE and fails. Do not end REGEX with `$`, so that it matches both the old heading and the tombstone heading.
- The script reports a block that it finds intact in another file as IN OTHER FILE. This does not fail. The reviewer makes sure that the move or the deduplication was planned.
- If no file with the name of a deleted file survives, a reference to it is DANGLING. If another file has that name, the line is AMBIGUOUS. This passes, but you must look at each AMBIGUOUS line by hand. The name match ignores case.

If the project has a Markdown linter or another formatter, run it too. Accept no new error types.

### 8. Write the results file

Record what the pass cut and why, and the before and after size table. Also record the path and size of the backup.
Add a line that says the backup stays until the user approves its deletion.
Keep the file outside the workspace, or mark it as transient. Otherwise the next trim pass cuts it as history.

### 9. Review independently (read-only reviewer)

The reviewer runs in a fresh context, not the planner's. It works from the backup and the trimmed workspace with the reviewer brief in [references/role-briefs.md](references/role-briefs.md).
The reviewer also reads the lines right next to each protected block. Added text there, such as an `Update:` line, can reverse the decision.

Severity rule: a lost protected item or a lost needed fact is High or Critical. Bloat is Medium or Low.
Each blocking finding gives the file and line, why it is wrong, and how to show that it fails. If the reviewer cannot show the failure, it says so.

### 10. Fix the findings (fixer)

The fixer applies fixes for accepted findings and restores lost facts from the backup. Then it reruns step 7 with the same flags.
Run a new review on the fix only. When the review has no High or Critical finding, stop. Also stop after 2 fix rounds. Then report what remains to the user.

### 11. Clean up

Delete the transient files: the plan folder, progress files, edit lists, and scratch copies.

Then write the final message of the pass. Every pass ends with this message. This includes a pass that stops early, is blocked or fails. The message must:

1. State each backup that still exists, with its path and size.
2. State each other leftover that still exists, with its path. Examples are a scratch copy, the plan folder and the results file.
3. Offer to delete the backup, and ask the user.

If the user approves, delete the backup. Do this last.
If the user declines or gives no answer, leave the backup in place. Repeat its path in the last message.
A pass is not done until the user knows about every leftover.

### 12. Keep it trim (ongoing hygiene)

These habits keep the next pass small:

- Rewrite, do not append. At the end of a run, fold new facts into the current-state sections of context files. Delete the log lines that produced them.
- Context files hold the present: decisions in force, current state, open items, key paths and the next step. They hold no changelogs and no per-session logs.
- If a decision changes before it is built, rewrite every place that carried the old one. Leave no "updated on" trails and no "superseded by" chains.
- If an old decision was built and its shape explains the current one, keep a note about it. Delete other history.
- If a new answer arrives, search for the old wording and fix every hit.
- If a review round or a work round closes, delete its records.

## Roles and models

- The planner and the reviewer use the strongest reasoning level available.
- The executor and the fixer use a cheaper level.
- The user's explicit model choice always wins.
- If the agent platform has an orchestration skill, follow it for dispatch and model choice.
- The planner, the executor and the reviewer run in separate contexts, so that nobody grades their own work.
- If rate limits matter, run the agents one at a time.

If the agent platform has no subagents, run the roles one after another in one context. Then give the review (step 9) to a fresh session or to the user. Give the re-review of step 10 to a fresh context too. If no fresh reviewer is available, tell the user that the pass has no independent review.

Briefs with placeholders for all four roles are in [references/role-briefs.md](references/role-briefs.md).

## Crash safety

Long runs keep a progress file. It holds a `STATUS` line, a list of steps, an append-only log, the current draft, and the next action. Update it at every step. On resume, read it first and continue from the next action. When the pass is done, delete it.

## Light path

Use the same protections inline. Work in this order:

1. Do step 1 of the full pass, with its glob, id regexes and protected-block regexes.
2. Copy the whole folder to a backup folder outside the workspace, for example with `cp -a FOLDER BACKUP`. Then tell the user the path and size of the backup.
3. Classify each file with a profile. List each cut with its anchor and a reason from the cut table. List the fixes for references that a deletion breaks. Prove that each anchor matches once.
4. Before you delete a file, ask the user. List each planned tombstone too. This is the deletion gate of step 5.
5. Apply the approved cuts. Remove words, not line breaks.
6. Run `python3 -I "${CLAUDE_SKILL_DIR}/scripts/trim_report.py" --before BACKUP --after FOLDER` with the regexes and one `--allow-changed` for each approved tombstone. Use one glob that covers every file that can cite the trimmed files. Do not narrow the glob to the trimmed files. Fix every failure.
7. Show the user the size table and a short list of what went. Then end the pass with the final message of step 11, and follow its three cases.

## Common failure modes

- Measuring lines instead of bytes, so joined lines pass as cuts.
- Paraphrasing protected text instead of keeping it byte-identical.
- A protected regex that covers more than the byte-identical text, so that permitted cuts fail.
- Cutting a fact that only one source cites, or a source that a kept fact uses.
- Renumbering or reusing ids after a deletion.
- Dangling references to deleted files or removed headings.
- Trimming without a backup, which leaves no way to prove that nothing was lost.
- Trimming everything at once, with no deletion gate and no pilot batch.
- Over-trimming a research file so that a claim loses its source or its uncertainty marker.
- A backup or a scratch copy left behind that the user does not know about.

## Reference files

- [references/cut-rules.md](references/cut-rules.md): the cut table, depth rules, row rules, byte targets and the tombstone template. Read it before planning.
- [references/artifact-profiles.md](references/artifact-profiles.md): keep and cut rules per artifact type.
- [references/plan-template.md](references/plan-template.md): the plan format and the anchor proof script.
- [references/role-briefs.md](references/role-briefs.md): briefs for the planner, executor, reviewer and fixer.
- [scripts/trim_report.py](scripts/trim_report.py): the size table and integrity tests. Run it with `--help` for all flags.
