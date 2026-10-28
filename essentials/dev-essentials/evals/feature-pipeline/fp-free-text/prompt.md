---
description: The task is a plain request, and the project context has no task provider. The run must write a task context, make the change, and commit it. It must not stop for a provider.
tags: [feature-pipeline, route]
plugins: ["../../.."]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill with a plain request as the task, and not a task ID. The arguments are: `add a method IsLowStock(string sku, int threshold) to StockService. If GetQuantity(sku) is less than threshold, it returns true. Add a test for it. --no-worktree --skip=simplifier,plan-artifact --commit-mode=per-step`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.

Take the recommended option for each stage question, and do not ask me.
