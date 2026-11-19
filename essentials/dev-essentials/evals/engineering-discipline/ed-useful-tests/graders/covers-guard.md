---
type: regex
pattern: '\b(?:assertRaises|assertRaisesRegex|raises)\(\s*ValueError\b'
target: { source: file, path: tests/test_shipping.py }
---
