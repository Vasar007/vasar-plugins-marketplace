---
type: regex
pattern: 'is None|is not None|or ""|or ''''|not user\.name|if user\.name\b'
target: { source: file, path: src/users.py }
---
