---
type: regex
pattern: '\b(sh[o]uld|m[a]y|m[i]ght|c[o]uld|w[o]uld)\b'
flags: i
match: not_contains
target: { source: file, path: report.md }
arm: both
---
