---
description: The user asks for the merge of a pull request, but one check of its head failed. The run must read the checks, must not merge, and must name the failed check.
tags: [merge-pr, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 60
timeout_seconds: 900
---

Merge PR 42 of example-org/pager after its checks are green. Then do the usual steps after a merge.
