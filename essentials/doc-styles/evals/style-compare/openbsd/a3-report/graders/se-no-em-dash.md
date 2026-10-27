---
type: regex
pattern: '\u2014'
match: not_contains
target: { source: file, path: report.md }
arm: both
---
