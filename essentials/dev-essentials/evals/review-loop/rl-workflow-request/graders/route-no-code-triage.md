---
type: regex
pattern: '"name":"Workflow","input":\{[^\n]*?(?:\.includes\(\w+\.severity\)|\b\w+\.severity\s*(?:===?|!==?|<=?|>=?)|\[\w+\.severity\]\s*(?:<=?|>=?))'
match: not_contains
target: trace
---
