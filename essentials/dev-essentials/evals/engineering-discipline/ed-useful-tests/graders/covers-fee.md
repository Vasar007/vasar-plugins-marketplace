---
type: regex
pattern: '(?:Equal\(\s*|,\s*|==\s*|\bassert\s+|=\s*)(?:[\w.]*\.)?shipping_fee\(\s*[\w.*-]'
target: { source: file, path: tests/test_shipping.py }
---
