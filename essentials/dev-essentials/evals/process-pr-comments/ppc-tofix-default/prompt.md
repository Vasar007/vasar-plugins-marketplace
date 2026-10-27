---
description: A reviewer marks one thread as ToFix. The run must fix the code, commit the fix, and post a reply that starts with the AI marker. The push must wait for the go-ahead, and the run must not resolve the thread.
tags: [process-pr-comments, mocks, smoke]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager.
