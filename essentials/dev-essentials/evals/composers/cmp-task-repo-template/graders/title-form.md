---
type: regex
pattern: '^(?:#[ \t]+|[*_]*title[*_]*[ \t]*:[*_]*[ \t]*`?)fix\([a-z][\w-]*\):[ \t]+\S'
flags: mi
target: { source: file, path: notes/Tasks/task-report-crash.md }
---
