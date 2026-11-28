---
type: regex
pattern: '^[ \t]*1[.)][ \t]+\S[^\n]*\n(?:[^\n]*\n)*?[ \t]*2[.)][ \t]+\S'
flags: m
target: { source: file, path: notes/Tasks/task-report-email.md }
---
