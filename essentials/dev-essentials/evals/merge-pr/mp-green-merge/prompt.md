---
description: The user asks for the merge of a pull request whose checks are green. The run must read the checks, merge with a squash that has a title and a body, and do the steps after the merge.
tags: [merge-pr, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 60
timeout_seconds: 900
---

Merge PR 42 of example-org/pager after its checks are green. Then do the usual steps after a merge.
