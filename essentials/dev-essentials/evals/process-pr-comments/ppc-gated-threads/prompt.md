---
description: A reviewer asks a question and marks one thread as out of scope. In the default mode, the answer to the question stays a draft, and the new issue waits for the go-ahead. The run must not change code.
tags: [process-pr-comments, mocks]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager.
