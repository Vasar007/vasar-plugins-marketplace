---
description: The same ToFix thread, with the autonomous flag. The run must fix the code, commit, reply, push, and resolve the thread, and it must not stop for a go-ahead.
tags: [process-pr-comments, mocks]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager. Use autonomous.
