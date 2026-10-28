---
type: regex
pattern: '^#|^\s*[-*] |\*\*'
flags: m
match: not_contains
target: last_message
arm: both
---
