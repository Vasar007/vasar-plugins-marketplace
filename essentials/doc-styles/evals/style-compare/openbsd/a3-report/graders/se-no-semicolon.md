---
type: regex
pattern: '^(?!    |\t|```|~~~)[^\n]*\x3b(?=[^\n]*(?:\n(?!```)[^\n]*)*(?:\n```[^\n]*(?:\n(?!```)[^\n]*)*\n```[^\n]*(?:\n(?!```)[^\n]*)*)*(?![\s\S]))'
flags: m
match: not_contains
target: { source: file, path: report.md }
arm: both
---
