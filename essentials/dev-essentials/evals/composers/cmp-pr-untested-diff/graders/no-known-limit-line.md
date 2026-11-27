---
type: regex
pattern: '^[^\n]*\b(?:review findings?|open findings?|known limits?|kept on purpose|on purpose)\b'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
