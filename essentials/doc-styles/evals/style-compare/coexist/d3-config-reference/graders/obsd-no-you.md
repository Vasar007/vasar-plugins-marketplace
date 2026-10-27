---
type: regex
pattern: '\by[o]u\b'
flags: i
match: not_contains
target: { source: file, path: docs/snapsync.conf.md }
arm: both
---
