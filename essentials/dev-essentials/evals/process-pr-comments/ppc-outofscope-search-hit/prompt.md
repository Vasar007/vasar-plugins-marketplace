---
description: "A reviewer marks one thread as out of scope and asks for a separate issue. The run is in the full mode. The issue search returns two issues. The body of one issue has the Source line with the URL of the thread. The other issue has a closer title, but it comes from another pull request. The run must use the issue with the matching Source line. So it creates no issue, asks no question about a new issue, and posts the reply that names that issue."
tags: [process-pr-comments, mocks, outofscope]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager. Use --mode full.
