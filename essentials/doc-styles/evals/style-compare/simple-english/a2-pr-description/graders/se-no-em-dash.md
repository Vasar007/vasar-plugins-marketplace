---
type: regex
pattern: '\u2014'
match: not_contains
target: { source: file, path: pr.md }
arm: both
---
