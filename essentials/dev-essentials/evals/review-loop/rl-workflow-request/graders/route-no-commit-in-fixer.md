---
type: regex
pattern: '"name":"Workflow","input":\{[^\n]*?(?:\bagent\(|=|\breturn\b)(?:\s|\\n)*(?:`(?!(?:[^`\\]|\\\\`|\\.)*?(?:[Dd][Oo] [Nn][Oo][Tt] edit|[Rr]ead-only))(?=(?:[^`\\]|\\\\`|\\.)*?(?:\bAPPLY\b|[Yy]ou are the fixer|\$\{[\w.]*[Ff]ixe?r?\w*[Rr]ules?\}))(?=(?:(?:[^`\\]|\\\\`|\\.)*?(?:\.\s|\\n))?(?:(?!(?:\b[Nn][Oo][Tt]\b|\b[Nn][Ee][Vv][Ee][Rr]\b|n\x27t\b|\b[Nn]o\b))[^.`\\])*?\b[Cc]ommit\b)|\x27(?![^\x27\n]*?(?:[Dd][Oo] [Nn][Oo][Tt] edit|[Rr]ead-only))(?=[^\x27\n]*?(?:\bAPPLY\b|[Yy]ou are the fixer|\$\{[\w.]*[Ff]ixe?r?\w*[Rr]ules?\}))(?=(?:[^\x27\n]*?\.\s)?(?:(?!(?:\b[Nn][Oo][Tt]\b|\b[Nn][Ee][Vv][Ee][Rr]\b|n\x27t\b|\b[Nn]o\b))[^.\x27\\])*?\b[Cc]ommit\b))'
match: not_contains
target: trace
---
