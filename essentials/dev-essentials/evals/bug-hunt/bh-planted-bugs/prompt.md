---
description: A bug hunt on a small shop project with three planted bugs, one known bug in a notes file, and one decoy. The run must report the three planted bugs, and it must not report the known bug or the decoy as new. The project must stay unchanged.
tags: [bug-hunt, smoke]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite, TaskCreate, TaskList, TaskUpdate]
max_turns: 200
timeout_seconds: 3600
---

Run a bug hunt on ./project with --report-dir=./reports --report-file=bug-hunt-report.md --base=none --known=./project/NOTES.md --areas=3 --hunter-model=opus. Use ./scratch as the scratch folder.
