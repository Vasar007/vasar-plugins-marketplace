---
type: regex
pattern: '^[ \t]*#{1,6}[ \t]*What\b'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
