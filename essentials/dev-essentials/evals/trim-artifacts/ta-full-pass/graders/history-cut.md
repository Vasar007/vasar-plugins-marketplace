---
type: regex
pattern: 'first tried a Redis cache'
match: not_contains
target: { source: file, path: notes/decisions.md }
---
