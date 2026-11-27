---
type: regex
pattern: '^[ \t]*(?:[-*+]|\d+\.)[ \t]+\[[xX]\][^\n]*\btests?\b'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
