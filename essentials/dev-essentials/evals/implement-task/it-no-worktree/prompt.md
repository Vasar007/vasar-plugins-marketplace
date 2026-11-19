---
description: "The run works one task with --no-worktree and --no-simplify in the full mode. The clone is on main, so the run must create its branch first and make no worktree. It must end with one task commit and no push."
tags: [implement-task, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials implement-task command on this task: lower the HTTP retry limit of the users app from 5 to 3. The arguments are `--base=main --no-worktree --no-simplify --notes-dir=notes --rounds=1 --mode full`. Work on a new branch named `eval/retry-limit`.

Do not push the branch. I push it myself.
