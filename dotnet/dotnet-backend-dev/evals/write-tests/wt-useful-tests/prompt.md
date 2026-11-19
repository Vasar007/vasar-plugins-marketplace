---
description: The command writes tests for one class with public constants and a property that has no logic, next to a method with real logic. The tests must cover the method and a guard, and they must pass. No test asserts only that a constant or the property has its value.
tags: [write-tests, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 120
timeout_seconds: 2400
---

/write-tests ShippingFeeCalculator -- On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
