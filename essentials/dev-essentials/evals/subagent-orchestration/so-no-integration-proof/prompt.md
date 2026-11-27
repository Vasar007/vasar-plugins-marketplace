---
description: A change of a pricing rule in a small Python app that has only unit tests. No smoke run, integration test, or end-to-end test exists. The route graders show whether the final reply says that this proof is missing, or whether the run ran the real CLI by hand.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Orchestrate this: members now get 15 percent off instead of 10 percent. Change the pricing rule, and commit the change.
