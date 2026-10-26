---
description: A small lookup task with the word orchestrate. The run must name the settings file and the value. The report shows how many subagents the run starts.
tags: [subagent-orchestration, route, smoke]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Orchestrate this: find where the HTTP retry limit is set and tell me its value.
