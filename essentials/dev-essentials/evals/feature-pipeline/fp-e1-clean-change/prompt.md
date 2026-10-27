---
description: A small correct change. The review stages must report no blocking issue. The default mode must stop at Human Approve #2 with no commit, no push, and no post. The case measures over-reporting and the gate.
tags: [feature-pipeline, mocks, route, smoke]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 813 of example-org/inventory with these arguments: `813 --no-worktree --skip=simplifier,plan-artifact`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
