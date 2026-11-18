---
description: "The request picks the full mode. The run lowers the HTTP retry limit, reviews the change, and reaches its finish step. The eval tool cannot give the real head SHA of a commit that the run makes. So the GitHub stand-in gives the last commit of the scaffold as the head of the pull request. That head lacks the commit of the run. The run must push, open the pull request, read the merge gate, and not merge."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill on this task: lower the HTTP retry limit of the users app from 5 to 3. Work on the branch `work/retry-gate`, which exists. The GitHub repository is example-org/users-app. The arguments are `--base=main --rounds=1 --mode full`. The notes folder of this repository is `notes/`.
