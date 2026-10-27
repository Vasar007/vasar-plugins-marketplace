---
type: regex
pattern: '## Blocking Issues(?:\\r)?\\n(?:(?:\\r)?\\n)?- \[ \] (?!<|\[<|\*\*\[HIGH\]\*\* <|None\b)'
match: not_contains
target: trace
---
