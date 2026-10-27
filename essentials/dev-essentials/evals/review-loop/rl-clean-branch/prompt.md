---
description: Control case. A branch adds a correct clamp function with full tests. The loop must find nothing to fix, so it must make no fix commit, and it must give a summary with a stop verdict.
tags: [review-loop]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on this branch with --rounds 2.
