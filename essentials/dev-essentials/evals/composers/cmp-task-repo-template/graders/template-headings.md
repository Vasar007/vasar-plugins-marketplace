---
type: regex
pattern: '^## What happens[ \t\r]*\n[\s\S]*?^## Steps to reproduce[ \t\r]*\n[\s\S]*?^## Expected result[ \t\r]*$'
flags: m
target: { source: file, path: notes/Tasks/task-report-crash.md }
---
