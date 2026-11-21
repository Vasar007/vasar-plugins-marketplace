---
description: "The run reviews pull request 7 with --post=2. The pull request has a real defect, a style defect, and a TODO comment. The table then has a major row, a minor row, and an info row. The style defect is row 2. The run must write the HTML artifact and edit no code. It must post one review comment, and that comment must be the style defect."
tags: [help-review-pr, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 100
timeout_seconds: 1800
---

Run `/dev-essentials:help-review-pr` on the pull request `https://github.com/example-org/pager/pull/7` with the argument `--post=2`.
