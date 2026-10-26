---
description: The command writes tests for each class of a folder. Each class gets a test file that uses the assertion library, and all tests must pass.
tags: [write-tests, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

/write-tests src/Billing.Domain/Pricing -- On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
