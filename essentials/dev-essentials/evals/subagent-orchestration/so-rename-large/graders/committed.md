---
type: regex
pattern: '\tcommit: (?!fixture:)'
target: { source: file, path: .git/logs/HEAD }
---
