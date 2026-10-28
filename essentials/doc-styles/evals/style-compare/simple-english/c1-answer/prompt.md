---
description: The model answers a user question about exit status 3 in the chat.
name: se-c1-answer
tags: [style-compare, style-compare-se]
plugins: ["../../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: if a writing-style skill is installed for this kind of text, load it with the Skill tool before you write English text, and follow it. The rule covers files and your reply, not only documentation.'
---

A user asks: "snapsync exited with code 3 last night, and the oldest snapshot is still there. Why, and what do I do?"

Answer in this chat. Do not write a file.

Facts:

- If the remote disk is full, the exit status is 3, and `snapsync` deletes no snapshot.
- The deletion of old snapshots starts after the new snapshot is complete, oldest first.
- The fix is to free space on the remote, or to lower `-k`. Then run `snapsync` again.

Use only these facts.
