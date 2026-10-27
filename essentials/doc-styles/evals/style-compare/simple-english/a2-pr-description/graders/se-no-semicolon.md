---
type: regex
pattern: '^(?!    |\t|```|~~~)[^\n]*\x3b'
flags: m
match: not_contains
target: { source: file, path: pr.md }
arm: both
---
