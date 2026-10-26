---
type: regex
pattern: 'Location: [^\n]*notify/retry\.py:(?:10|11|12|13|14)\b'
target: { source: file, path: reports/bug-hunt-report.md }
---
