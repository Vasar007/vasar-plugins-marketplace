---
description: The request picks the full mode. The case shows the chain from Step 9 to Step 9b and the stop at a failed merge gate. The eval tool cannot give the real head SHA of a commit that the run makes. So the GitHub stand-in gives the last commit of the scaffold as the head of the PR. That PR lacks the commit of the run. The run must open the PR, read the merge gate, and not merge.
tags: [feature-pipeline, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 200
timeout_seconds: 3600
---

Use the dev-essentials feature-pipeline skill on issue 823 of example-org/inventory with these arguments: `823 --no-worktree --skip=simplifier,plan-artifact --mode full`.

On this machine, MSBuild can use only one process. Pass -m:1 to every dotnet build and dotnet test command. Tell each subagent to do the same.
