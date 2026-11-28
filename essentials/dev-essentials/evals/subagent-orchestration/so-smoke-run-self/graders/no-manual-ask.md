---
type: regex
pattern: '\b(?:please|can\s+you|c[o]uld\s+you|w[o]uld\s+you|you\s+(?:can|sh[o]uld|m[a]y|m[i]ght|need\s+to|will\s+need\s+to|have\s+to))\s+(?:\w+\s+){0,2}?(?:run|print|try)\b|(?:^|[.:]\s+)(?:run|print)\s+\x60[^\x60\n]+\x60\s+(?:on|at)\s+(?:that|the)\s+(?:machine|shop|computer|printer)'
flags: i
match: not_contains
target: last_message
---
