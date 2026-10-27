---
description: The default branch is checked out and the request has the autonomous flag. The run must make a branch, commit there, and push only that branch.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode with --autonomous for this task: add a method IsInStock(string sku) to StockService. If GetQuantity for the sku is more than 0, IsInStock returns true. Add a test for it.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
