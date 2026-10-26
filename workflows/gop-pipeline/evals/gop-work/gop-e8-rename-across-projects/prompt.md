---
description: The task renames a public method that another project and the tests call. The run must update every caller and keep the tests green.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: rename the public method StockService.GetQuantity to GetAvailableQuantity. Update every caller.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
