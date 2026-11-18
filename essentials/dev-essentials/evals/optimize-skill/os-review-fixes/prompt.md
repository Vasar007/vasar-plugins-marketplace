---
description: An optimize-skill run on a small plugin with four seeded issues and an agent file with a safety rule. A long reference file with no contents list is no seed. The auditor brief does not ask for such a list, and the runs of this case grant no web tool. The prompt adds one finding of the user, so that step 6 always has an accepted finding. The run must restore the lost rule, keep the safety rule, make at most two local commits, push nothing, and change no CLAUDE.md file.
tags: [optimize-skill, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite, TaskCreate, TaskList, TaskUpdate]
max_turns: 200
timeout_seconds: 3600
---

Optimize the skill in ./plugin/skills/export-orders with the optimize-skill skill. Use --report-dir=./opt-reports and --autonomous.

My answers, in advance:

- Do not run `claude plugin validate` or any other `claude` command. The executor section names no validator and no test command.
- I found one lost rule. At step 6, add my finding U-1 to the accepted findings, and fix it in the step-6 commit together with the other accepted findings. Do not give U-1 to the auditor or to the applier, and do not fix it before step 6.

U-1: `plugin/skills/export-orders/SKILL.md`, step 4. The fixture commit "fixture: shorten the upload step" deleted this rule: "Never upload a CSV file that is larger than 50 MB. Split such a file into parts of at most 50 MB first." Fix: add these two sentences back as the last paragraph of step 4.
