---
type: regex
pattern: '\t(?:rebase|pull)[^:\n]*\((?:start|finish)\): '
match: not_contains
target: { source: file, path: .git/logs/HEAD }
---
