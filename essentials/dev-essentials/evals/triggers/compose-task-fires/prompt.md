---
description: If the user asks for a task description in chat, the compose-task skill starts, and the task-composer agent does not. The prompt asks for no file, because a trigger run has no tool that writes a file. Then the session has no reason to try the wrapper agent.
tags: [triggers, compose-task]
allowed_tools: [Skill, Agent, Read, Glob, Grep]
---

Write a task description for a retry with backoff in the order export job. Return the description in chat, and do not write a file.
