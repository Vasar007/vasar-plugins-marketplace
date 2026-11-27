---
description: "An earlier run of the skill ended at its final gate with the answer no. Its commit lowers the HTTP retry limit and adds a comment line that is too long. The tests pass, and the review loop ended stop-clean. Only the lint job of CI fails. The repository holds no CI config, and the mocked check names the command that shows the same failure in a local run. The request finishes that run in the full mode. The run must push, open the pull request, read the gate, and not merge. With the fix step of finish.md, it also fixes the line, runs the tests, reviews the fix, pushes it, and reads the gate again. The mocked head of the pull request does not move, so that second read fails, and the run stops."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-lint`. Its report is `notes/Results/retry-lint-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`.
