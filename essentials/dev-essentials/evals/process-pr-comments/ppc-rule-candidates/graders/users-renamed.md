---
type: regex
pattern: '^(?![\s\S]*\bdisplayName\b)[\s\S]*\ndef display_name\(user\):'
target: { source: file, path: src/users.py }
---
