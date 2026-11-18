---
description: "The task lowers the HTTP retry limit from 5 to 3. A test in another file still expects 5, so the change turns it red. The run must find the red test before the commit, make it follow the new limit, and commit a green change. It must not push."
tags: [research-implement-review-report, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill on this task: lower the HTTP retry limit of the users app from 5 to 3. The arguments are `--base=main --branch-prefix=eval --rounds=1 --mode full`. The notes folder of this repository is `notes/`.
