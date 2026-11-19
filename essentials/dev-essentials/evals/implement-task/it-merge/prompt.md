---
description: "An earlier run of the implement-task command ended at its final gate with the answer no. Its commit lowers the HTTP retry limit, its review loop ended stop-clean, its simplify pass made no commit, and no remote holds its branch. The request asks to finish that run in the full mode. The run must push the branch, open the pull request, read the merge gate, and merge with a squash. It must make no new commit."
tags: [implement-task, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials implement-task command to finish the earlier run on the branch `work/retry-limit`. Its report is `notes/Results/retry-limit-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --notes-dir=notes --mode full`.
