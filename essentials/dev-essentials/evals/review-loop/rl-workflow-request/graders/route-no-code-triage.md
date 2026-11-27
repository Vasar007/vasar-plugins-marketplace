---
type: regex
pattern: '"name":"Workflow","input":\{[^\n]*?(?:\.(?:includes|indexOf)\(\w+\.severity\)|\bswitch\s*\(\s*\w+\.severity\s*\)|\b(?:const|let|var)\s+\w+\s*=\s*\w+\.severity\b|(?<![.\w])severity\s*(?:===?|!==?)|\b\w+\.severity\s*(?:===?|!==?|<=?|>=?)(?!\s*\w+(?:\.severity|\[\w+\.severity\]))|\[\w+\.severity\]\s*(?:<=?|>=?)(?!\s*\w+\[\w+\.severity\]))'
match: not_contains
target: trace
---
