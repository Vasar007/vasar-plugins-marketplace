---
type: regex
pattern: '\t(?:commit(?: \(cherry-pick\))?|cherry-pick): (?!fixture:)[\s\S]*\t(?:commit(?: \(cherry-pick\))?|cherry-pick): (?!fixture:)|\t(?:commit \(merge\)|merge [^:\n]+): [\s\S]*\t(?:commit \(merge\)|merge [^:\n]+): '
target: { source: file, path: .git/logs/HEAD }
---
