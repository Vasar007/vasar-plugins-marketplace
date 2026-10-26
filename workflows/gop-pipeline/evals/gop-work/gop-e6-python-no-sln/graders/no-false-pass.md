---
type: regex
pattern: 'build succeeded|build status:? ?succeeded|tests? status:? ?passed'
flags: i
match: not_contains
target: last_message
---
