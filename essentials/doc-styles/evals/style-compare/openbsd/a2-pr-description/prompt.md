---
description: The model writes the pull request description of a change to snapsync.
name: obsd-a2-pr-description
tags: [style-compare, style-compare-openbsd]
plugins: ["../../../.."]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: if a writing-style skill is installed for this kind of text, load it with the Skill tool before you write English text, and follow it. The rule covers files and your reply, not only documentation.'
---

Write `pr.md`, the description of a pull request.

The change:

- `src/xfer.c`: when the remote returns `ENOSPC`, stop, delete nothing, and exit with status 3. Before the change, the exit status was 1, and it came after the deletion of the oldest snapshot.
- `tests/test_full.c`: a new test for a full disk.
- `docs/cli.md`: the exit status 3 is new.
- Reason: issue #212. A user lost a snapshot on a full disk.
- `-k` does not change.

Use only these facts.
