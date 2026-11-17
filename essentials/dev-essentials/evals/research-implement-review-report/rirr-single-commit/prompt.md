---
description: "A plan file with two tasks lowers the HTTP retry limit and the timeout of the users app. The run uses the single-commit mode, so it makes at least two commits. It must squash them into one commit on top of main with the squash script of the plugin, and it must not push."
tags: [research-implement-review-report, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill on the plan file `notes/Plans/retry-and-timeout-plan.md`. The arguments are `--base=main --branch-prefix=eval --rounds=1 --commit-mode=single --autonomous`. The notes folder of this repository is `notes/`.
