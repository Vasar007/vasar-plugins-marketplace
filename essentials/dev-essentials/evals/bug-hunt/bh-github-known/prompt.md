---
description: A bug hunt with a GitHub source of known issues. Issue 17 describes the cache key bug, so the run must list it as known and must not report it as new. The run must not write to GitHub.
tags: [bug-hunt, mocks]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite, TaskCreate, TaskList, TaskUpdate]
max_turns: 200
timeout_seconds: 3600
---

Run a bug hunt on ./project with --report-dir=./reports --report-file=bug-hunt-report.md --base=none --known=./project/NOTES.md --areas=3 --hunter-model=opus --github=example-org/shop. Use ./scratch as the scratch folder.
