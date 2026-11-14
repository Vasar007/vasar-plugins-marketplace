---
type: regex
pattern: '\tcommit: (?!fixture:)'
target: { source: file, path: .git/run-commits.log }
---
