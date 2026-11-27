---
description: "The planted state of rirr-gate-fix-full, in the partial mode. The request gives the yes of the final gate in advance. The run must push the branch, open the pull request, read the gate, and not merge. It must push no second time. With the fix step of finish.md, it fixes the line in a local commit and reviews the fix. Then it asks before the push of the fix."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-lint`. Its report is `notes/Results/retry-lint-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode partial`. The notes folder of this repository is `notes/`. My answer to the question of the final gate is yes: push the branch, open the pull request, and merge it after the gate of merge-pr.
