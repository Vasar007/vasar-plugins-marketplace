---
description: A branch adds page_slice, and the last item of each page is lost. The loop must find the defect, fix it, and commit the fix. A correct function in ranges.py must stay as it is. The loop must not push. The prompt gives the contract for page < 1 in advance, because a run has no user to ask.
tags: [review-loop, smoke, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on this branch with --rounds 2.

I am away during the run, so here is my answer in advance. For `page < 1`, `page_slice` must raise `ValueError`, as it does for `size <= 0`.
