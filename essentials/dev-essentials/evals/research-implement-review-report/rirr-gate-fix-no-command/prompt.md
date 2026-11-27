---
description: "An earlier run of the skill ended at its final gate with the answer no. Its commit lowers the HTTP retry limit and adds a comment line that is too long for the lint script of the clone. The tests pass. The check lint is red, and the merge state is unstable. No CI configuration names the command of the check, and no job log exists. So the check is a stop. The request finishes that run in the full mode. The run must push, open the pull request, read the gate, and name the failed check. It must make no commit, push no second time, and not merge."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-lint`. Its report is `notes/Results/retry-lint-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`.
