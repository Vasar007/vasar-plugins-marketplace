---
description: "The user asks for a task description of a bug in plain words, with the steps in a sentence and no version. The run must write the draft file with numbered steps to repeat the bug, an actual result, an expected result, and a version line with the commit of the repository or the word unknown."
tags: [composers, route]
allowed_tools: [Skill, Agent, Read, Glob, Grep, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Write a task description for this bug. The feature name is report-email. The user report stops with an error when a user has an email address with no @ sign, for example `guest`. To see it, add a user with the email `guest` to the example users and build the report. The build stops with an IndexError. The report must still show a line for that user, with an empty domain.
