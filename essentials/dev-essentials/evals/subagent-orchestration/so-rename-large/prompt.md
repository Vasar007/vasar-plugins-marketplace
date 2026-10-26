---
description: A multi-stage rename in a large repo with 25 callers. The run must rename fetch_user to load_user in every caller, also in the deepest folder, run the tests, and commit. The report shows how many subagents the run starts.
tags: [subagent-orchestration, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Orchestrate this multi-stage task: find every caller of fetch_user, rename it to load_user everywhere, run the tests, and commit the change.
