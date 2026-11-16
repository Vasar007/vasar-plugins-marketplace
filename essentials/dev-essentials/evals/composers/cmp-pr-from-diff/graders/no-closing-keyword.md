---
type: regex
pattern: '\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#12\b'
flags: i
match: not_contains
target: { source: file, path: Notes/PRs/PR-user-tasks-12-customer-index.md }
---
