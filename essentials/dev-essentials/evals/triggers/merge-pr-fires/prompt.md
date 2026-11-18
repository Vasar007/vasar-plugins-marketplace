---
description: If the user asks for the merge of a pull request by its URL, the merge-pr skill starts. The git-sync skill and the process-pr-comments skill do not.
tags: [triggers, merge-pr]
allowed_tools: [Skill, Read, Glob, Grep]
---

Merge <https://github.com/example-org/pager/pull/42> after its checks are green.
