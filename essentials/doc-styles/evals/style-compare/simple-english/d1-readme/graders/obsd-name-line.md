---
type: regex
pattern: '^snapsync(\.conf)?[ ]-[ ][a-z][^.\n]*$'
flags: m
target: { source: file, path: README.md }
arm: both
---
