---
description: The task renames a public method that another project and the tests call. The run must update every caller and keep the tests green.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 881 of example-org/inventory with these arguments: `881 --no-worktree --skip=simplifier,plan-artifact --commit-mode=per-step`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
