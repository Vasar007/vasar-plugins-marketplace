---
description: Probe of the mock setup. It checks that a mock of a second plugin answers a call from the session, and that a subagent can call the mocked tool.
tags: [probe]
plugins: ["../../..", "../../_stubs/github"]
allowed_tools: [Read, Glob, Grep, Agent]
max_turns: 30
timeout_seconds: 600
---

Read pull request 42 of example-org/pager with the GitHub tool pull_request_read. Use method get. Then start one general-purpose subagent. The subagent reads the same pull request with the same tool and returns its title. In your answer, give the head SHA and the title.
