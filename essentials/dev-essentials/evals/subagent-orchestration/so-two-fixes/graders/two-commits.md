---
type: regex
pattern: '\tcommit: (?!fixture:)'
match: "count:2"
target: { source: file, path: .git/run-commits.log }
---
