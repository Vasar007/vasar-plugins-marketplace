---
description: An untracked file sits in the repo before the run. The commit must not take it, and the final report must list it as not committed.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: if the sku is empty or only white space, SkuFormatter.Normalize must throw an ArgumentException. Add a test for it.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
