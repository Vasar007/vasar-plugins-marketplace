---
type: regex
pattern: '^(?=[\s\S]*\bREQ-1\b)(?=[\s\S]*\bREQ-2\b)(?=[\s\S]*\bREQ-3\b)(?=[\s\S]*\bREQ-4\b)(?=[\s\S]*\bREQ-5\b)(?=[\s\S]*\bREQ-6\b)'
target: { source: file, path: notes/requirements.md }
---
