---
description: "The repository has a bug template and a feature template, and the prompt names neither. The user asks for a task description of a bug. The draft must use the headings of the bug template in their order. It must have no section of the default form and no comment of the template. Its title takes the form of the template. The final reply names the label of the template."
tags: [composers, route]
allowed_tools: [Skill, Agent, Read, Glob, Grep, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Write a task description for this bug. The feature name is report-crash. If a user has an email address with no @ sign, for example `guest`, the user report stops with an error. To see it, add a user with the email `guest` to the example users and build the report. The build stops with an IndexError. The report must still show a line for that user, with an empty domain.
