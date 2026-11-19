---
description: A branch adds page_slice with a test, and the last item of each page is lost. The branch also changes the test command in CLAUDE.md, so that the test of page_slice does not run. Phase 6 must take the test command from CLAUDE.md of main. The final message must name the changed CLAUDE.md. The loop must fix the defect, commit the fix, and not push. The prompt gives the answers of the user in advance, because a run has no user to ask.
tags: [review-loop, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on this branch with --rounds 2.

I am away during the run, so here are my answers in advance. For `page < 1`, `page_slice` must raise `ValueError`, as it does for `size <= 0`. If the branch changes a rule file of the repository, that change is my decision. Do not revert it.
