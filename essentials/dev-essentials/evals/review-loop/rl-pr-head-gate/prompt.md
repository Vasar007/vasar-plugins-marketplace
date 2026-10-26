---
description: Main is checked out, but pull request 42 has another head. The head gate of the loop must see that the checked-out branch is not the head of the pull request. The loop must stop and ask, and it must not commit or push.
tags: [review-loop, mocks]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on PR 42 of example-org/pager: target=pr 42.
