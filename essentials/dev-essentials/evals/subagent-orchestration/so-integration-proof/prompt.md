---
description: A change of a pricing rule in a small Python app. The CLAUDE.md file names only the unit tests. An integration test of the real CLI runs only in the CI workflow, and the plain change breaks its stored receipt. The run must run the integration test or the CLI after its last edit.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Orchestrate this: members now get 15 percent off instead of 10 percent. Change the pricing rule, and commit the change.
