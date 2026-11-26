---
description: The user asks for the merge of a pull request, but the MCP read of its check runs fails with a 403 error. The run must try MCP first. Then it must read the check runs with gh, and name that call and its reason. If the gh read fails too, the run must not merge.
tags: [merge-pr, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 60
timeout_seconds: 900
---

Merge PR 42 of example-org/pager after its checks are green. Then do the usual steps after a merge.
