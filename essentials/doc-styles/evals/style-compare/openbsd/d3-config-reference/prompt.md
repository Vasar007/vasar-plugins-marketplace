---
description: The model writes the reference of the snapsync configuration file from a fact sheet.
name: obsd-d3-config-reference
tags: [style-compare, style-compare-openbsd]
plugins: ["../../../.."]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: if a writing-style skill is installed for this kind of text, load it with the Skill tool before you write English text, and follow it. The rule covers files and your reply, not only documentation.'
---

In the OpenBSD man-page style, write `docs/snapsync.conf.md`, the reference of the configuration file of snapsync.

Facts about the file:

- The configuration file has one directive on each line. A `#` starts a comment.
- `keep count`: the default is 30. The `-k` flag overrides it.
- `port number`: the default is 22.
- `exclude pattern` and `include pattern`: the patterns are globs. Each directive can repeat. The last match decides.
- `bandwidth rate`: the rate is in KB/s. 0 means no limit, and it is the default.
- A `source path { ... }` block sets `keep` and `exclude` for one source.
- An unknown directive stops `snapsync` with exit status 1 and the message `line N: unknown directive`.

Use only these facts.
