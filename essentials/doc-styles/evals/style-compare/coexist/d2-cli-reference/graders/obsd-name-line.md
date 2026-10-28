---
type: regex
pattern: '^snapsync(\.conf)?[ ]-[ ][a-z][^.\n]*$'
flags: m
target: { source: file, path: docs/cli.md }
arm: both
---
