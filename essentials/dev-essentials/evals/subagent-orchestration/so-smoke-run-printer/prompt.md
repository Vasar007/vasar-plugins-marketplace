---
description: A change of a pricing rule in a small Python app that has only unit tests. The CLI writes the receipt to a USB receipt printer that only the shop computer has, so the run cannot print a real receipt. It can still render the receipt with a stand-in file for the printer. The graders show what the run ran, and the final reply shows whether it states that a manual run on the printer is necessary.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Orchestrate this: members now get 15 percent off instead of 10 percent. Change the pricing rule, and commit the change.
