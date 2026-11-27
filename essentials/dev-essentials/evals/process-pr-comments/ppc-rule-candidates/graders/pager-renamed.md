---
type: regex
pattern: '^(?![\s\S]*\bpageCount\b)[\s\S]*\ndef page_count\(items, size=DEFAULT_PAGE_SIZE\):'
target: { source: file, path: src/pager.py }
---
