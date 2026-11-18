---
description: "A plan file with one task lowers the HTTP retry limit. The request names no mode, so the run is in the partial mode. After the report, the run must ask one question about the push, the pull request, and the merge. It must push nothing before the answer."
tags: [research-implement-review-report, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill on the plan file `notes/Plans/retry-limit-plan.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --branch-prefix=eval --rounds=1`. The notes folder of this repository is `notes/`.
