---
type: regex
pattern: '^HTTP_RETRY_LIMIT = 3$'
flags: m
target: { source: file, path: config/settings.py }
---
