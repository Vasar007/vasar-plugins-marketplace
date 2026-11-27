---
description: The base probe of candidate M1. The user asks for a workflow run and a review loop in one request. The branch and the planted defect are the same as in rl-off-by-one. The loop must keep its triage before the first fix, dispatch a reviewer that does not fix, fix the defect, and commit the fix. A run can call the Workflow tool only with a grant of that tool. Two route graders show whether the run had the tool and whether it called it.
tags: [review-loop, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Use a workflow to run a review loop on this branch with --rounds 2.

I am away during the run, so here is my answer in advance. For `page < 1`, `page_slice` must raise `ValueError`, as it does for `size <= 0`.
