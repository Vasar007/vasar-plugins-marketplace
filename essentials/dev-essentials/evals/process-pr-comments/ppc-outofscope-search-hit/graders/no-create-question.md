---
type: regex
pattern: '\bcreate\b[^\n?]{0,200}\?'
flags: i
match: not_contains
target: last_message
---
