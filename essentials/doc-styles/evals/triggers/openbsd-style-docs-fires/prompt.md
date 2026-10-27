---
description: If the user asks to rewrite a README in the style of an OpenBSD man page, the openbsd-style-docs skill starts.
tags: [triggers, openbsd-style-docs]
plugins: ["../../..", "../../../../dev-essentials", "../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
---

Rewrite this README in the style of an OpenBSD man page:

```markdown
# snapsync 🚀

**snapsync** is a blazing-fast, powerful tool that makes backups effortless!

## Features

- Copies a snapshot of a local directory to a remote host over SSH
- Keeps a fixed number of snapshots on the remote
- Prints what it would do with `-n`

## Options

- `-k count`: keep `count` snapshots. The default is 30.
- `-n`: print the transfers, and change nothing.
```
