---
type: regex
pattern: '^[^\n]*\b(?:expected|actual) (?:result|behaviou?r)\b|^[ \t]*(?:#{1,6}[ \t]*|[*_]*)Steps to (?:reproduce|repeat)\b'
flags: mi
match: not_contains
target: { source: file, path: notes/Tasks/task-customer-index.md }
---
