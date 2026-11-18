---
description: "A reviewer marks one thread as out of scope and asks for a separate issue. The run is in the full mode. The issue search finds no issue for the thread. In the full mode, the run creates the issue with no question. The issue has the Source line of the thread, and the reply of the run names the new issue. The scored grader is the issue search, which both sides of a compare run. The route graders hold the new end state."
tags: [process-pr-comments, mocks, outofscope, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager. Use --mode full.
