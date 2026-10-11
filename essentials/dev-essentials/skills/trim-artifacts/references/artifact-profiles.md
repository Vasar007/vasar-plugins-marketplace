# Artifact profiles

Classify each file with one profile before you plan it. If a file mixes types, use the profile of its largest part. Default targets are in [cut-rules.md](cut-rules.md).

## A. Design and plan documents

- Keep decisions, specifications, requirements, paths, commands, milestones, risks, chosen tools and action items for the user.
- Cut narrative, rejected alternatives beyond one row each, step logs of finished work, and restated context.
- The target is 50 to 65 percent of bytes.

## B. Research notes

- Keep the findings that a decision, a requirement, a risk or an open question uses. Keep each with its source URL, its date and any uncertainty marker.
- Cut search narration, findings that nothing uses, audit-log bulk, and long quotes where one line says the same.
- The target is 20 to 50 percent of bytes. Never cut the only source of a kept claim.

## C. State and handoff files

- Keep decisions in force, current state, open items, key paths and the next step.
- Cut changelogs, "what was done", per-session logs, review-cycle narration and superseded counts.
- The target is 40 to 60 percent of bytes. Rewrite the file in place. Do not append a summary.

## D. Agent-memory files

- Keep the frontmatter with the name unchanged, and a one-line description under about 150 characters. Keep each index hook under about 150 characters too. Then keep the rule, a Why line, and a How-to-apply line.
- Keep every instruction, condition, exception and concrete value, without exception. Do not add rules or reinterpret them.
- Cut dates, stories of how a rule came about, "seen in session X" narration, repeated restatements, and precedent lists.
- Merge duplicates by cross-linking, not by deleting a file. Other memories and the index link to it.
- Replace stale counts and snapshots with a pointer to the live source.
- Make sure that each file has one index line and that every link resolves. Re-read the backup to find any dropped instruction.
- There is no fixed byte target.

## E. Logs and changelogs

- Keep the facts that nothing else records and that a future reader needs. Fold them into the owning file.
- Once its facts live in the owning files, cut the log itself.
- The target is 0 to 20 percent of bytes, or delete the file through the deletion gate.

## F. Task and issue lists

- Keep open items with their id, one-line goal, assignee, and blocking condition. Keep closed items as one line with the id and the outcome.
- Cut discussion threads, status history, and duplicated descriptions of linked items.
- The target is 30 to 60 percent of bytes. Never drop or renumber an id.
