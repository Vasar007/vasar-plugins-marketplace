---
type: regex
pattern: '\by[o]u\b'
flags: i
match: not_contains
target: { source: file, path: docs/cli.md }
arm: both
---
