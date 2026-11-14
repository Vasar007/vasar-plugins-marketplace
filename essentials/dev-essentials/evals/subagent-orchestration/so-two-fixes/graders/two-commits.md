---
type: regex
pattern: '\t(?:commit(?: \(merge\))?|cherry-pick|merge [^:\n]+): (?!fixture:)'
match: "count:2"
target: { source: file, path: .git/logs/HEAD }
---
