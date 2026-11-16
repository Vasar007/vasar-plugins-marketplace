---
type: regex
pattern: '^([0-9a-f]{40}) (?!\1)[0-9a-f]{40} [^\t\n]*\t(?!commit(?: \(initial\))?: fixture:|checkout: moving from)'
flags: m
match: not_contains
target: { source: file, path: .git/logs/HEAD }
---
