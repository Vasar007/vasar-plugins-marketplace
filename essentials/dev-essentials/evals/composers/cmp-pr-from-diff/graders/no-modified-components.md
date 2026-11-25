---
type: regex
pattern: '^ {0,3}(?:#+ *|\*\*)Modified Components\b'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
