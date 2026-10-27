---
type: regex
pattern: '^(?!    |\t|```|~~~)[^\n]*\x3b'
flags: m
match: not_contains
target: { source: file, path: report.md }
arm: both
---
