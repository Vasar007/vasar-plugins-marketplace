---
description: An earlier run ended after Step 9. The change is committed and pushed, PR 77 is open, and the state file lists each stage as done. The request starts the pipeline again in the full mode. The checks of the PR are green. The run must go to Step 9b, read the merge gate, and merge the PR with a squash.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 822 of example-org/inventory with these arguments: `822 --no-worktree --skip=simplifier,plan-artifact --mode full`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
