---
description: A cheap bug hunt with one area and Sonnet agents at medium effort. It tests the flow and not the recall. The run must end with a final report and delete the scratch folder and each progress file. It must keep the run context file and leave the project unchanged.
tags: [bug-hunt, flow, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite, TaskCreate, TaskList, TaskUpdate]
max_turns: 200
timeout_seconds: 3600
---

Run the bug-hunt skill on ./project with --report-dir=./reports --report-file=bug-hunt-report.md --base=none --known=./project/NOTES.md --areas=1 --hunter-model=sonnet --hunter-effort=medium --verifier-model=sonnet --verifier-effort=medium --auditor-model=sonnet --auditor-effort=medium. Use ./scratch as the scratch folder.
