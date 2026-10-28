---
type: regex
pattern: '^(?!    |\t|```|~~~)[^\n]*\x3b(?=[^\n]*(?:\n(?!```)[^\n]*)*(?:\n```[^\n]*(?:\n(?!```)[^\n]*)*\n```[^\n]*(?:\n(?!```)[^\n]*)*)*(?![\s\S]))'
flags: m
match: not_contains
target: last_message
arm: both
---
