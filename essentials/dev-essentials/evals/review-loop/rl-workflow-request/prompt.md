---
description: The user asks for a workflow run and a review loop in one request (issue 390). The branch and the planted defect are the same as in rl-off-by-one. The loop must keep its triage before the first fix and dispatch a reviewer that does not fix. It must fix the defect and commit the fix after the tests. A run can call the Workflow tool only with a grant of that tool. Then the graders read the script of the Workflow call. route-no-code-triage fails a script that sorts the findings by severity in code.
tags: [review-loop, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Use a workflow to run a review loop on this branch with --rounds 2.

I am away during the run, so here is my answer in advance. For `page < 1`, `page_slice` must raise `ValueError`, as it does for `size <= 0`.
