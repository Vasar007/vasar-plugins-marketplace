---
description: The PR creation entry of the project context names the repository of the PR and the owner of a fork. The run must push the branch and open the PR on the GitHub stand-in. The head of the PR is the fork owner and the branch.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 821 of example-org/inventory with these arguments: `821 --no-worktree --skip=simplifier,plan-artifact --autonomous`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
