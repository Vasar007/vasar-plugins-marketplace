---
description: A branch adds page_slice, and the last item of each page is lost. CLAUDE.md names a lint command, and the lint already fails on main, because a vendored file has an unused import. The loop must fix the defect and commit the fix. Phase 6 must run the lint after the tests, and the failed lint must lead to the script failure_check.py and to stop-blocked. The loop must not change the lint script or the vendored file, and it must not push. The prompt gives the contract for page < 1 in advance, because a run has no user to ask.
tags: [review-loop, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on this branch with --rounds 2.

I am away during the run, so here is my answer in advance. For `page < 1`, `page_slice` must raise `ValueError`, as it does for `size <= 0`.
