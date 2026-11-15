---
type: regex
pattern: '\bcreate\b(?:(?![.!]\s)[^\n?]){0,200}\?'
flags: i
match: not_contains
target: last_message
---
