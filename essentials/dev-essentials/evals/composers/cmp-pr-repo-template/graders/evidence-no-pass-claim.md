---
type: regex
pattern: '^## Evidence\b(?:(?!\n## )[\s\S])*?\b(?:pass(?:es|ed|ing)?|verif(?:y|ies|ied)|succeed(?:s|ed)?|green)\b'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
