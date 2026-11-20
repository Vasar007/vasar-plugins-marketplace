---
type: regex
pattern: '\t(?:commit(?: \((?:amend|merge|cherry-pick|initial)\))?|cherry-pick|revert|merge [^:\n]+): (?!fixture:)'
match: not_contains
target: { source: file, path: .git/logs/HEAD }
---
