---
description: If the user asks to fix markdownlint warnings, the openbsd-style-docs skill does not start.
tags: [triggers, openbsd-style-docs]
plugins: ["../../..", "../../../.deps/dev-essentials", "../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
---

Fix the markdownlint warnings in README.md:

````markdown
# snapsync

snapsync copies a snapshot of a local directory to a remote host.
Report bugs at https://example.org/snapsync/issues
## Install
Run this:
```
make install
```
## Options
* `-k count`: keep count snapshots.
- `-n`: print the transfers.
````
