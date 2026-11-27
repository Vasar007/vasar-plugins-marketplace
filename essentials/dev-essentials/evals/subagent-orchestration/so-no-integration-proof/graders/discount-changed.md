---
type: regex
pattern: '(?:^|[^\w.])(?:15|85|0?\.15|0?\.85)(?![\w.])'
target: { source: file, path: app/pricing.py }
---
