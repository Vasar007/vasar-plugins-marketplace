---
description: "An earlier run of the skill ended at its final gate with the answer no. Its commit lowers the HTTP retry limit. The tests pass, and the review loop ended stop-clean. After the last fetch of the clone, another commit reached main on the remote. So the pull request is behind its base, and its checks pass. The request finishes that run in the full mode. The run must push, open the pull request, read the gate, and not merge. With the fix step of finish.md, it also fetches the base, merges it into the branch, runs the tests, pushes, and reads the gate again. The mocked head of the pull request does not move, so that second read fails, and the run stops."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-behind`. Its report is `notes/Results/retry-behind-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`.
