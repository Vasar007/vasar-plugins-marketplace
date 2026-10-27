---
description: The task changes a package version in a shared build file. The pipeline must run all tests, because any test can break.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 841 of example-org/inventory with these arguments: `841 --no-worktree --skip=simplifier,plan-artifact --commit-mode=per-step`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
