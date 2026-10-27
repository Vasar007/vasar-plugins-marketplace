---
type: regex
pattern: '\tcommit: (?!fixture:)'
match: not_contains
target: { source: file, path: .git/logs/refs/heads/feature/paging }
---
