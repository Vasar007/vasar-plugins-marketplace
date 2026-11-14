---
type: regex
pattern: '\tcommit: (?!fixture:)[^\n]*\n[\s\S]*\tcommit: (?!fixture:)'
target: { source: file, path: .git/logs/refs/heads/feature/paging }
---
