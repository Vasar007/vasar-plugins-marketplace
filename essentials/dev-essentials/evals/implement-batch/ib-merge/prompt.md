---
description: "An earlier run of the implement-batch skill with two tasks ended at its final gate with the answer no. Its two task commits change two HTTP settings, each review loop and the final review ended stop-clean, and no remote holds its branch. The request asks to finish that run in the full mode. The run must push the branch, open the pull request, read the merge gate, and merge with a squash. It must make no new commit."
tags: [implement-batch, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials implement-batch skill to finish the earlier run on the branch `work/retry-batch`. Its report is `notes/Results/retry-batch-report.md`. The GitHub repository is example-org/users-app. The arguments are `--base=main --plan-dir=notes/Plans --mode full`.
