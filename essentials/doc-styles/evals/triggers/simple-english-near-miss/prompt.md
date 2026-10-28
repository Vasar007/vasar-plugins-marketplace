---
description: If the user asks for plain English for non-native readers, the openbsd-style-docs skill does not start, and the reply drops the jargon.
tags: [triggers, openbsd-style-docs]
plugins: ["../../..", "../../../.deps/dev-essentials", "../../../eval-stubs/simple-english"]
allowed_tools: [Skill, Read, Glob, Grep]
---

Rewrite this README intro in plain English for non-native readers:

```text
snapsync leverages an SSH-based delta-transfer pipeline to idempotently materialize point-in-time snapshots of a source tree on a remote host, with a retention policy that garbage-collects the oldest snapshots once the configured cardinality is exceeded.
```
