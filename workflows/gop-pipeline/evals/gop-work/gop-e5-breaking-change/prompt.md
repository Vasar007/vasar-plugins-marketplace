---
description: A cache in GetQuantity breaks an existing test unless Restock clears it. The run must fix the code and keep the test as it is.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: add an in-memory cache to StockService.GetQuantity, so that a repeated read of one sku does not query the database again.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
