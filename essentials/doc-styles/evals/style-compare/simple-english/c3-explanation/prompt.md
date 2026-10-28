---
description: The model explains in the chat what the -k flag changes.
name: se-c3-explanation
tags: [style-compare, style-compare-se]
plugins: ["../../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: if a writing-style skill is installed for this kind of text, load it with the Skill tool before you write English text, and follow it. The rule covers files and your reply, not only documentation.'
---

Explain in this chat what `-k` changes. Say when the user lowers it. Do not write a file.

Facts:

- `-k count`: keep `count` snapshots on the remote, and delete the older ones. The range is 1 to 365. The default is 30.
- The deletion starts after the new snapshot is complete, oldest first.
- A failed transfer deletes nothing.

Use only these facts.
