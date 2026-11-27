---
type: regex
pattern: '\t(?:merge [^:\n]+|commit \(merge\)|pull(?: [^:\n]+)?): '
target: { source: file, path: .git/logs/HEAD }
---
