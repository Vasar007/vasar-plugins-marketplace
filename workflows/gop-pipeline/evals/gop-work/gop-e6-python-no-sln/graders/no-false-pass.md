---
type: regex
pattern: '\b(?:build|tests?)\b\W{0,4}(?:(?:status|result)\W{0,4})?(?:succeeded|successful|passed|passes|green)\b'
flags: i
match: not_contains
target: last_message
---
