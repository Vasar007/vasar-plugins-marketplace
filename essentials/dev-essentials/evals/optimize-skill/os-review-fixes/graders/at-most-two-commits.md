---
type: regex
pattern: '\tcommit(?: \((?!amend\))[a-z-]+\))?: (?!fixture:)[\s\S]*\tcommit(?: \((?!amend\))[a-z-]+\))?: (?!fixture:)[\s\S]*\tcommit(?: \((?!amend\))[a-z-]+\))?: (?!fixture:)'
match: not_contains
target: { source: file, path: .git/logs/HEAD }
---
