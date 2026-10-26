---
description: The task changes a package version in a shared build file. The pipeline must run all tests, because any test can break.
tags: [gop-work, route]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use GOP mode for this task: update the NUnit package from 4.6.1 to 5.0.0 in Directory.Packages.props.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
