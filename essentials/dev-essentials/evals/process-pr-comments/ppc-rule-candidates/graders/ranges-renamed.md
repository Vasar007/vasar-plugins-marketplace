---
type: regex
pattern: '^(?![\s\S]*\blastPage\b)[\s\S]*\ndef last_page\(count\):'
target: { source: file, path: src/ranges.py }
---
