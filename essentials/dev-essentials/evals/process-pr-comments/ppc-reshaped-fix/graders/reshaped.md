---
type: regex
pattern: 'islice\( ?items ?, ?start ?, ?start ?\+ ?size ?\)|(\w+) = start ?\+ ?size\b(?! ?[-+*/])[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*islice\( ?items ?, ?start ?, ?\1 ?\)'
target: { source: file, path: src/pager.py }
---
