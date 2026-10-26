---
description: A small correct change. The validators must not report a critical finding. The case measures over-reporting.
tags: [gop-work, smoke, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: if the amount is 0 or less, StockService.Restock must throw an ArgumentOutOfRangeException. Add a test for it.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
