---
description: The model writes the plan to add a bandwidth flag to snapsync.
name: se-a1-plan
tags: [style-compare, style-compare-se]
plugins: ["../../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: before you write English text, load the simple-english:simple-english skill with the Skill tool, and follow it. The rule covers files and your reply.'
---

Write `plan.md`, the plan to add the flag `-b rate` to snapsync.

Facts:

- `src/main.c` parses the flags with `getopt`.
- `src/conf.c` reads the configuration.
- `src/xfer.c` already reads `conf->bandwidth`.
- `make test` runs the tests in `tests/`.
- The new flag `-b rate` limits the bandwidth like the `bandwidth` directive. The flag overrides the directive.
- 0 means no limit.
- A value above 1000000 is an error, with exit status 1.

Use only these facts.
