---
description: "An earlier run of the skill ended at its final gate with the answer no. Its commit lowers the HTTP retry limit, its review loop ended stop-clean, and no remote holds its branch. The request asks to finish that run in the full mode. The run must push the branch, open the pull request, read the merge gate, and merge with a squash. It must make no new commit."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-limit`. Its report is `notes/Results/retry-limit-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`.
