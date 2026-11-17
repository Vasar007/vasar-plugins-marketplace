---
type: regex
pattern: 'def page_slice\([^\n]*\n(?:\s+"""[^\n]*"""\n)?\s+if size <= 0:\n\s+raise ValueError'
target: { source: file, path: src/pager.py }
---
