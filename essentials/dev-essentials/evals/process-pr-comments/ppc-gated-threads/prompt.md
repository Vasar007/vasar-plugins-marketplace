---
description: A reviewer asks a question and marks one thread as out of scope. In the default mode, the answer to the question stays a draft. The issue search finds no issue for the out-of-scope thread, and the new issue waits for the go-ahead. All replies of the cycle wait for one batch after the answers of the user, so the run posts no reply. The run must not change code.
tags: [process-pr-comments, mocks, outofscope]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager.
