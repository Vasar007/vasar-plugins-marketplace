---
name: trim-artifacts
description: >-
  Trim pass for text artifacts such as notes, plans, handoff files, agent
  memory, and logs. It removes history, process residue, and duplication, and
  keeps decisions, ids, needed facts, and uncertainty markers.
when_to_use: >-
  Use it for "trim", "compact", "clean up notes", or "this memory is bloated".
  Do not use it for source code. Use /simplify for that.
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
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

To turn on `--interactive` or `--autonomous`, the user writes the flag in the request.

## The algorithm (full pass)

### 1. Settle scope and the protect-set

Ask the user for the protect-set, or infer it. Without `--interactive`, infer it, write it into the plan, and report it in one status line. Then plan. With `--interactive`, get the approval of the user before you plan. The protect-set has four parts:

1. Declared decisions are text that the user declared as their decision. Keep it byte-identical. You can cut agent-written framing around it. If the user declared a requirement word for word, it is byte-identical too.
2. Identifiers are ids that other files and people cite. Detect id families by pattern, then show the list to the user. Never renumber or reuse an id.
3. Needed facts are recommendations, fallback plans, requirements, open questions with defaults, risks and chosen tools. Every requirement that the user did not declare word for word is a needed fact. Keep each fact with the source (URL and date) of each claim that it uses.
4. Uncertainty markers are labels such as "unverified" or "assumption". Without them, a guess reads as a fact.

Parts 1 and 2 form the byte-identical tier. Parts 3 and 4 form the substance tier.

Other verbatim user text is not in the protect-set. If it duplicates protected text, you can delete it. Never paraphrase it. Keep it verbatim, or remove it.

Then build the glob and the regexes with [references/protect-set.md](references/protect-set.md). One glob covers every file that can cite a trimmed file.

Make sure that each regex matches at least once in the workspace.

Also settle the byte targets (defaults are in [references/cut-rules.md](references/cut-rules.md)), the backup location, and who approves deletions.

### 2. Back up the workspace

Before the first edit, copy the whole workspace to a location outside it, for example with `cp -a WORKSPACE BACKUP`.
The script refuses a `--before` path that equals, contains, or sits inside the `--after` path. It cannot find a stray copy that you do not pass to it, or a backup inside the workspace in the subfolder form. Keep every copy outside the workspace.
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

The planner proves each anchor with a script. Then it makes two copies of every file that the glob matches in the workspace, not only of its batch. It puts them in a scratch folder: an `orig` copy and a `target` copy. Each copy keeps the relative paths, so that a regex with a path still matches. It applies the plan to `target` and runs `scripts/trim_report.py` against `orig`, with one `--allow-changed` for each proposed tombstone. This is the dry run.
Keep plans and scratch copies outside the workspace, so that the pass does not measure or trim them.

Measure bytes, not lines. Joining lines is not a cut, because the bytes stay. Remove words instead. If a file stays above its target, the plan says why.

### 5. Gate the deletions

Before any deletion, show the user these lists:

1. The files to delete, with a one-line reason each.
2. Files or records that the user approved for deletion before the pass, to show the real scope.
3. The protected items that the plan withdraws as tombstones, each with its file and its `--allow-changed` regex (see step 7).

Under the lists, add one line that reminds the user of the path of the backup.

Deletions and tombstones are destructive. Wait for explicit approval of each item. If the user rejects an item, the planner removes it from the plan and reruns the dry run.
This gate stays without `--interactive` too, because deletions and tombstones destroy data. With `--autonomous`, it does not stop. Put the three lists into the final message, and continue. The backup keeps a copy of each deleted file.
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

Exit code 0 means pass. Exit code 1 means an integrity failure. Exit code 2 means a usage error. Before you write the `--glob` and `--allow-changed` flags, read [references/script-results.md](references/script-results.md). Read it again before you act on the result. Look at each AMBIGUOUS line by hand.

If the project has a Markdown linter or another formatter, run it too. Accept no new error types.

### 8. Write the results file

Record what the pass cut and why, and the before and after size table. Also record the path and size of the backup.
Add a line that says the backup stays until the user approves its deletion.
Keep the file outside the workspace, or mark it as transient. Otherwise the next trim pass cuts it as history.

### 9. Review independently (read-only reviewer)

The reviewer runs in a fresh context, not the planner's. It works from the backup and the trimmed workspace with the reviewer brief in [references/role-briefs.md](references/role-briefs.md). Fill `{PLAN_PATH}` with the plan path of every batch. The plans stay until step 11, so the reviewer can test each moved block against them.
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
3. Offer to delete the backup, and ask the user. With `--autonomous`, keep the backup, and give its path.

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

## Crash safety

Long runs keep a progress file. It holds a `STATUS` line, a list of steps, an append-only log, the current draft, and the next action. Update it at every step. On resume, read it first and continue from the next action. When the pass is done, delete it.

## Light path

Use the same protections inline. Work in this order:

1. Do step 1 of the full pass, with its glob, id regexes and protected-block regexes.
2. Copy the whole folder to a backup folder outside the workspace, for example with `cp -a FOLDER BACKUP`. Then tell the user the path and size of the backup.
3. Classify each file with a profile. List each cut with its anchor and a reason from the cut table. List the fixes for references that a deletion breaks. Prove that each anchor matches once.
4. Before you delete a file or write a tombstone, run the deletion gate of step 5. Show its three lists, and follow its rules for each mode.
5. Apply the approved cuts. Remove words, not line breaks.
6. Run `python3 -I "${CLAUDE_SKILL_DIR}/scripts/trim_report.py" --before BACKUP --after FOLDER` with the regexes and one `--allow-changed` for each approved tombstone. Use one glob that covers every file that can cite the trimmed files. Do not narrow the glob to the trimmed files. Read the result as step 7 says, and fix every failure.
7. Show the user the size table and a short list of what went. Then end the pass with the final message of step 11, and follow its three cases.

## Reference files

- [references/cut-rules.md](references/cut-rules.md): the cut table, depth rules, row rules, byte targets and the tombstone template. Read it before planning.
- [references/artifact-profiles.md](references/artifact-profiles.md): keep and cut rules per artifact type.
- [references/plan-template.md](references/plan-template.md): the plan format and the anchor proof script.
- [references/protect-set.md](references/protect-set.md): the glob, the id regexes and the protected-block regexes of step 1.
- [references/script-results.md](references/script-results.md): how to read the result of the script in step 7.
- [references/role-briefs.md](references/role-briefs.md): briefs for the planner, executor, reviewer and fixer.
- [scripts/trim_report.py](scripts/trim_report.py): the size table and integrity tests. Run it with `--help` for all flags.
