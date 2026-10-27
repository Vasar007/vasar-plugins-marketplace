---
description: A multi-stage rename in a small repo. The run must rename fetch_user to load_user in every caller, run the tests, and commit. The report shows how many subagents the run starts.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Orchestrate this multi-stage task: find every caller of fetch_user, rename it to load_user everywhere, run the tests, and commit the change.
