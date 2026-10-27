---
type: regex
pattern: 'recent_orders[\s\S]{0,600}(?:LIMIT|fetchmany\( ?\w|\[:\s*\w+\])'
target: { source: file, path: src/store.py }
---
