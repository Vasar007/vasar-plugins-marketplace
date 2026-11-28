---
description: "An earlier run of the skill ended at its final gate with the answer no. Its commit lowers the HTTP retry limit, but the test still expects the old limit, so the tests fail. The review loop ended stop-clean. The request finishes that run in the full mode. The graders show whether the run fixes the test before the push, pushes, and opens the pull request, or stops at the red test."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-red`. Its report is `notes/Results/retry-red-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`.
