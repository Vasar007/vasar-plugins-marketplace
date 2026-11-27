---
type: regex
pattern: '^[^\n]{89,}$'
flags: m
match: not_contains
target: { source: file, path: config/settings.py }
---
