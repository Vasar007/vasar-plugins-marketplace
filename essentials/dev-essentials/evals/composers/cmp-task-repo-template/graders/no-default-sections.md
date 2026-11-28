---
type: regex
pattern: '^#{1,6}[ \t]*(?:Current State Analysis|Changes to Do)\b'
flags: mi
match: not_contains
target: { source: file, path: notes/Tasks/task-report-crash.md }
---
