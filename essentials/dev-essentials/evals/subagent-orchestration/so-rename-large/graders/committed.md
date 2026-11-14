---
type: regex
pattern: '\t(?:commit(?: \(merge\))?|cherry-pick|merge [^:\n]+): (?!fixture:)'
target: { source: file, path: .git/logs/HEAD }
---
