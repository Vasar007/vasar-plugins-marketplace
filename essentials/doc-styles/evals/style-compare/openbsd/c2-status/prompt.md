---
description: The model gives a status update on a snapsync release in the chat.
name: obsd-c2-status
tags: [style-compare, style-compare-openbsd]
plugins: ["../../../.."]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: if a writing-style skill is installed for this kind of text, load it with the Skill tool before you write English text, and follow it. The rule covers files and your reply, not only documentation.'
---

Give a status update on the release in this chat. Do not write a file.

Facts:

- Release 2.4: 3 of 4 blockers are fixed. They are the exit status on a full disk, the IPv6 port parser, and the manual page.
- Open: the sparse file timeout on FreeBSD 14. The owner is Dana, and the fix is planned for 2026-11-03.
- The release moves from 2026-10-30 to 2026-11-06.
- The reader has nothing to do.

Use only these facts.
