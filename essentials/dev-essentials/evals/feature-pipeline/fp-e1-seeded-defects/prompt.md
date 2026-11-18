---
description: The issue dictates code with seven planted defects. A stage of the pipeline must name each defect. The final code must not hold the four defects that break the code or its security.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 811 of example-org/inventory with these arguments: `811 --no-worktree --skip=simplifier,plan-artifact --mode full`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.

Take the recommended option for each stage question, and do not ask me.

Do not stop before Stage 1. Let the stages ask their questions.
