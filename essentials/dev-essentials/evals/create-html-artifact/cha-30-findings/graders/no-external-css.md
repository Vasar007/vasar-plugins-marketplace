---
type: regex
pattern: '<link[^>]+stylesheet'
flags: i
match: not_contains
target: { source: file, path: review-findings.html }
---
