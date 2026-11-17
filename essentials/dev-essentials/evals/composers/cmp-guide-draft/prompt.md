---
description: "The user asks for a how-to guide as a local draft, and the notes hold a warning. The repository keeps its guide drafts in docs/drafts/, not in the default drafts folder of the skill. The run must save the guide in docs/drafts/ with the given file name, and write no file below Notes/Docs/. The guide starts with a title and a short overview. It holds numbered steps, a code block with a shell language tag, the test command of the notes, and the warning in a blockquote."
tags: [composers, route]
allowed_tools: [Skill, Agent, Read, Glob, Grep, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Write a short how-to guide for new developers: how to run the tests of this repository on their own machine. Keep it as a local draft with the file name `run-tests-locally.md`, and do not publish it. My notes: you need Python 3.11 or later. Run all tests with `python3 -m unittest discover -s tests`. Important: run the command in the root folder of the repository, because it looks for the `tests` folder in the current folder.
