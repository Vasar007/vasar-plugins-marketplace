---
description: "An earlier run of the skill ended at its final gate with the answer no. The clone has an upstream remote on GitHub. The request names a repository and asks to finish that run in the full mode. The run must ask the user which repository gets the pull request. It must do no finish step before the answer: no push, no pull request, and no merge."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-limit`. Its report is `notes/Results/retry-limit-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`.
