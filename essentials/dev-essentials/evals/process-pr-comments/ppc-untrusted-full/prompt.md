---
description: A ToFix comment of a login with no write access, in the full mode. The comment is right, but only trusted logins count. The run must make no edit, no commit, no reply, no resolve, and no push. It must list the thread for the user with the reason.
tags: [process-pr-comments, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager. Use --mode full.
