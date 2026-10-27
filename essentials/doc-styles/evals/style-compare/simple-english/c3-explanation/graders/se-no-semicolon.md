---
type: regex
pattern: '^(?!    |\t|```|~~~)[^\n]*\x3b'
flags: m
match: not_contains
target: last_message
arm: both
---
