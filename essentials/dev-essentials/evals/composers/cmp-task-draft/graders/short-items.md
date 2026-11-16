---
type: regex
pattern: '^## Changes to Do[\s\S]*?^[ \t]*(?:[-*]|\d+\.)[ \t]+(?:\S+[ \t]+){9,}\S+'
flags: m
match: not_contains
target: { source: file, path: Notes/Tasks/task-customer-index.md }
---
