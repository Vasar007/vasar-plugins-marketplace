---
type: regex
pattern: '"type":"assistant"[^\n]*Severity: CRITICAL\b(?! \|)(?!\x60)'
match: not_contains
target: trace
---
