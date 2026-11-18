---
description: A full trim pass on 12 notes files. The pass must cut two planted passages, delete the approved session log and its emptied folder, and fix the index line that cites the log. The decision blocks, the ids, and the uncertainty markers must stay. The backup must stay in the run folder.
tags: [trim-artifacts, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite, TaskCreate, TaskList, TaskUpdate]
max_turns: 200
timeout_seconds: 3600
---

Run a full trim pass on ./notes with the trim-artifacts skill and --mode full. Use the full pass with its agents, not the light path, and use one batch.

My answers, in advance:

- Backup: before the first edit, copy ./notes to ./trim-backup with `cp -a notes trim-backup`. At the end of the pass, keep the backup. Do not delete it.
- Put the plans, the scratch copies, the progress files, and the results file in ./trim-work.
- Protect-set: each decision block of notes/decisions.md (a `## DEC-n` heading, a `Quote:` line, and a `Decision:` line) stays byte-identical. The ids DEC-n, REQ-n, Q-n, RISK-n, and M-n stay. Each "(unverified" marker stays.
- Deletion gate: I approve the deletion of notes/archive/session-log-2026-10.md. I approve no other deletion and no tombstone.

When the pass ends, run `find notes trim-backup | sort > trim-listing.txt` in this folder. Then write your final message.
