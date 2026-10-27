---
description: A branch adds page_slice, and the last item of each page is lost. The loop must find the defect, fix it, and commit the fix. A correct function in ranges.py must stay as it is. The loop must not push.
tags: [review-loop, smoke, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on this branch with --rounds 2.
