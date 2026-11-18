---
type: regex
pattern: '\tcommit(?: \((?!amend\))[a-z-]+\))?: (?!fixture:)[\s\S]*\tcommit(?: \((?!amend\))[a-z-]+\))?: (?!fixture:)'
target: { source: file, path: .git/logs/HEAD }
---
