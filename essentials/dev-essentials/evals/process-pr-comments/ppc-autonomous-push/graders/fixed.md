---
type: regex
pattern: 'end = start \+ size\s*\n\s*return items\[start:end\]|items\[start:end \+ 1\]|items\[start:start \+ size\]'
target: { source: file, path: src/pager.py }
---
