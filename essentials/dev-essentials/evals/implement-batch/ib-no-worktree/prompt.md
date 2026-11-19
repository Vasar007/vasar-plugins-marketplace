---
description: "The run does two small tasks with --no-worktree in the full mode. The clone is on main, so the run must create its branch first and make no worktree. It must end with one commit for each task, at most one final review commit, and no push."
tags: [implement-batch, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials implement-batch skill on these two tasks of the users app:

1. In `config/settings.py`, set `HTTP_RETRY_LIMIT` to 3. The test `tests/test_http_client.py` expects 5, so change it to expect the new limit.
2. In `config/settings.py`, set `TIMEOUT_SECONDS` to 10. No test reads it.

The arguments are `--base=main --no-worktree --plan-dir=notes/Plans --rounds=1 --mode full`. Work on a new branch named `eval/retry-and-timeout`.

Do not push the branch. I push it myself.
