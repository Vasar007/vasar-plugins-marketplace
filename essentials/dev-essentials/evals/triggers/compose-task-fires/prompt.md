---
description: If the user asks for a task description in chat, the compose-task skill starts. The prompt asks for no file, because a trigger run has no tool that writes a file.
tags: [triggers, compose-task]
allowed_tools: [Skill, Read, Glob, Grep]
---

Write a task description for a retry with backoff in the order export job. Return the description in chat, and do not write a file.
