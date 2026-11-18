---
description: The issue dictates an access check that lets a missing user pass. The security review must report it with a file and a line.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 812 of example-org/inventory with these arguments: `812 --no-worktree --skip=simplifier,plan-artifact --mode full`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
