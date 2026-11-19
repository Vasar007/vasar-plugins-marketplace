---
description: The request loads engineering-discipline and asks for unit tests of one Python module. The module has public constants and one function that uses them. The tests must cover the function and a guard, and they must pass. No test asserts only that a constant has its value.
tags: [engineering-discipline, route]
allowed_tools: [Skill, Read, Glob, Grep, Agent, TodoWrite]
max_turns: 60
timeout_seconds: 900
---

Use the dev-essentials engineering-discipline skill for this work. Write unit tests for `app/shipping.py` in `tests/test_shipping.py`, and run them. Do not commit.
