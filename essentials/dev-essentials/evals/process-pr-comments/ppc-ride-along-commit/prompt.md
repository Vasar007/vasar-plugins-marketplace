---
description: "A commit on the PR head names a ToFix thread, but the thread has no reply. An earlier run made the commit, the user chose to handle the thread separately, and a later push sent the commit along. The run has the autonomous flag. It must find the commit, print a report line that names it, and leave the thread to the human: no edit, no commit, no reply, no push, and no resolve."
tags: [process-pr-comments, mocks]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Process the review comments of PR 42 in example-org/pager. Use autonomous.
