---
description: If the user asks for a man-page style reference of command-line options, the openbsd-style-docs skill starts.
tags: [triggers, openbsd-style-docs]
plugins: ["../../..", "../../../.deps/dev-essentials", "../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
---

Write a man-page style reference for the options of snapsync in docs/cli.md:

Usage: snapsync [-nqv] [-c file] [-k count] [-p port] source host:path

-c file: read the configuration from file. The default is /etc/snapsync.conf.
-k count: keep count snapshots on the remote, and delete the older ones. The range is 1 to 365. The default is 30.
-n: print the transfers, and change nothing. Not together with -q.
-p port: the SSH port. The default is 22.
-q: print errors only.
-v: print each file name.
