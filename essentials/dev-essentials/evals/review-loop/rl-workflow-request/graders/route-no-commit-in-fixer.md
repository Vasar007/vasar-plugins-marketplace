---
type: regex
pattern: '"name":"Workflow","input":\{[^\n]*?(?:\bagent\(|=|\breturn\b)(?:\s|\\n)*(?:`(?=(?:[^`\\]|\\\\`|\\.)*?(?:\bAPPLY\b|[Yy]ou are the fixer|\$\{[\w.]*[Ff]ixe?r?\w*[Rr]ules?\}))(?=(?:[^`\\]|\\\\`|\\.)*?(?<![Nn]ot )(?<![Nn]ever )(?<![Nn]o )\b[Cc]ommit\b)|\x27(?=[^\x27\n]*?(?:\bAPPLY\b|[Yy]ou are the fixer|\$\{[\w.]*[Ff]ixe?r?\w*[Rr]ules?\}))(?=[^\x27\n]*?(?<![Nn]ot )(?<![Nn]ever )(?<![Nn]o )\b[Cc]ommit\b))'
match: not_contains
target: trace
---
