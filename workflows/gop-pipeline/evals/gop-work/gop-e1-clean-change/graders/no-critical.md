---
type: regex
pattern: '"type":"assistant"[^\n]*Severity: CRITICAL(?:\\r)?\\n'
match: not_contains
target: trace
---
