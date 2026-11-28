---
description: A change of a pricing rule in a small Python app that has only unit tests. No smoke run, integration test, or end-to-end test exists, but the README names a command that prints the receipt of a sample order. The run can run the real CLI itself. The graders show whether it runs the CLI, and the final reply shows whether it asks the user for a manual run.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Orchestrate this: members now get 15 percent off instead of 10 percent. Change the pricing rule, and commit the change.
