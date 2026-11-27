---
type: regex
pattern: '\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+(?:(?:[\w.-]+/[\w.-]+)?#|https?://github\.com/[\w.-]+/[\w.-]+/issues/)(?:12|77)\b'
flags: i
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
