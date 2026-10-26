---
description: Two independent fixes, one in billing and one in shipping, each with a failing test. The run must fix both and make one commit for each fix. The report shows how many subagents the run starts.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Orchestrate this: fix the two failing tests in billing and shipping, and commit each fix on its own.
