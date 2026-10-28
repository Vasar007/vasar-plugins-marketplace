---
description: The default branch is checked out and the request has the autonomous flag. The run must make a branch, commit there, and push only that branch.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 831 of example-org/inventory with these arguments: `831 --no-worktree --skip=simplifier,plan-artifact --autonomous`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
