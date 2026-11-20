---
description: "The run works one task with --no-worktree in the full mode. A tracked file of the clone has a change of the user with no commit. So the run must stop before any work, name that file, and keep its change."
tags: [implement-task, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials implement-task command on this task: lower the HTTP retry limit of the users app from 5 to 3. The arguments are `--base=main --no-worktree --no-simplify --notes-dir=notes --rounds=1 --mode full`. Work on a new branch named `eval/retry-limit`.

Do not push the branch. I push it myself.
