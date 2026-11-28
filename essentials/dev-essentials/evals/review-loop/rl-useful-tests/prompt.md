---
description: A branch caps the page size and adds sort labels. It adds a constant with a test that mirrors its value. The sort labels have a test of one known key and of the fallback. It also changes total_pages and adds no test for it. No row of a review report asks for a test of each label, and the loop adds none. A report names the mirror test, and the loop adds a test of total_pages above the limit. The prompt gives the answers of the user in advance, because a run has no user to ask.
tags: [review-loop]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 150
timeout_seconds: 2400
---

Run a review loop on this branch with --rounds 2.

I am away during the run, so here are my answers in advance. The cap is the intended behavior: a size above `MAX_PAGE_SIZE` counts as `MAX_PAGE_SIZE`, and callers slice with `limited_size(size)`.
