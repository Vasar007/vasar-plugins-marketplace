---
type: regex
pattern: '\n[^\n]'
match: not_contains
target: { source: file, path: .remote/origin.git/logs/refs/heads/work/retry-lint }
---
