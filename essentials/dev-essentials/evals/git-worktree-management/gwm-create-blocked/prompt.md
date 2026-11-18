---
description: "The user asks for a worktree of a new branch and approves it in advance. The sandbox of an eval run keeps .git/worktrees read-only, so git worktree add fails. The run must call the create subcommand of worktree.py, and its final reply must say that the worktree was not made and why."
tags: [git-worktree-management, route]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Use the dev-essentials git-worktree-management skill. Create a worktree for the new branch `eval/tasks/42-add-paging` from `main`. I approve the worktree in advance, so do not ask me. At the end, tell me where the worktree is.
