---
type: regex
pattern: '\b(?:please|can\s+you|c[o]uld\s+you|w[o]uld\s+you|you\s+(?:can|sh[o]uld|m[a]y|m[i]ght|need\s+to|will\s+need\s+to|have\s+to))\b[^.\n?]{0,60}?\b(?:run|print|test|try|check|v[e]rify)\b'
flags: i
match: not_contains
target: last_message
---
