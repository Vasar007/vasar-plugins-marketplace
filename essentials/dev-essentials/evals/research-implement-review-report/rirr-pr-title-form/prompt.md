---
description: "An earlier run of the skill ended at its final gate with the answer no. Its commit lowers the HTTP retry limit, its review loop ended stop-clean, and no remote holds its branch. The repository has a PR template. A comment of the template gives the form of PR titles, and the request does not name the template. The request asks to finish the run in the full mode, with no merge. The run must push the branch and open the pull request. The title must have the form of the template, and the body must have the headings of the template. The run must not merge, and it must make no new commit."
tags: [research-implement-review-report, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials research-implement-review-report skill to finish the earlier run on the branch `work/retry-title`. Its report is `notes/Results/retry-title-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --mode full`. The notes folder of this repository is `notes/`. Push the branch and open the pull request, but do not merge it.
