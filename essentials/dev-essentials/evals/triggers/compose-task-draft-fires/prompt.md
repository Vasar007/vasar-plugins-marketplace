---
description: If the user asks for a task description with no mode, the compose-task skill starts. The default draft mode writes a file, and a trigger run has no tool that writes a file. So a run can start the wrapper agent task-composer, and the case has no grader on it. Kept runs show that a run can start an agent also with no Agent in allowed_tools.
tags: [triggers, compose-task]
allowed_tools: [Skill, Read, Glob, Grep]
---

Write a task description for a retry with backoff in the order export job.
