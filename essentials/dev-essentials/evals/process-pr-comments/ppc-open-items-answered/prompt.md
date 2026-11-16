---
description: "A reviewer asks a question and marks one thread as out of scope. The prompt gives the answers of the user in advance: post the answer to the question, and create the new issue. The run must finish both open items after the answers. So it creates the issue with the Source line of the thread, and then posts both replies in one batch. The reply of the out-of-scope thread names the new issue. The run must not change code."
tags: [process-pr-comments, mocks, outofscope]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager.

I am away during the run, so here are my answers to your questions in advance:

1. When you ask whether to post the reply to the [Question] thread, my answer is: yes, post it as drafted.
2. When you ask whether to create the issue for the [OutOfScope] thread, my answer is: yes, create it with your draft title.
