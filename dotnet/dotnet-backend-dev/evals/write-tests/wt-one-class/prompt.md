---
description: The command writes tests for one class. The tests must cover each public method and use the assertion library. They must pass, and the class must stay as it is.
tags: [write-tests, smoke, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 120
timeout_seconds: 2400
---

/write-tests InvoiceNumberGenerator -- On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
