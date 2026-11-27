---
description: "The planted state of rirr-gate-fix-full, in the interactive mode. The request gives the yes of the final gate in advance. The run must push the branch, open the pull request, read the gate, and not merge. It must make no commit, merge no base, and push no second time. With the fix step of finish.md, it reports the failed item. Then it asks the user about a fix."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-behind`. Its report is `notes/Results/retry-behind-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode interactive`. The notes folder of this repository is `notes/`. My answer to the question of the final gate is yes: push the branch, open the pull request, and merge it after the gate of merge-pr.
