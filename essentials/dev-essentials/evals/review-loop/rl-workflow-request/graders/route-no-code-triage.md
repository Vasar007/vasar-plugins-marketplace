---
type: regex
pattern: '"name":"Workflow","input":\{[^\n]*?(?:\.(?:includes|has)\(\w+\.severity\)|\.indexOf\(\w+\.severity\)\s*(?:[<>]=?|[!=]==?)|\bswitch\s*\(\s*\w+\.severity\s*\)|\b(?:const|let|var)\s+(\w+)\s*=\s*\w+\.severity\b[^\n]*?\b\1\s*(?:===?|!==?)|(?:\x27|\\"|`)\s*(?:===?|!==?)\s*\w+\.severity\b|(?<![.\w])severity\s*(?:===?|!==?)|\b\w+\.severity\s*(?:===?|!==?|<=?|>=?)(?!\s*\w+(?:\.severity|\[\w+\.severity\]))|\[\w+\.severity\]\s*(?:<=?|>=?)(?!\s*\w+\[\w+\.severity\]))'
match: not_contains
target: trace
---
