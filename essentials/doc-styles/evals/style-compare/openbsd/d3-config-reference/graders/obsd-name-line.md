---
type: regex
pattern: '^snapsync(\.conf)?[ ]-[ ][a-z][^.\n]*$'
flags: m
target: { source: file, path: docs/snapsync.conf.md }
arm: both
---
