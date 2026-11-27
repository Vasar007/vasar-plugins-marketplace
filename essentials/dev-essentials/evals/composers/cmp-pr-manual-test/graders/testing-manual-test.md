---
type: regex
pattern: '^## Testing\b(?=(?:(?!\n## )[\s\S])*?(?:\bby hand\b|\bmanual(?:ly)?\b|\bcopy of (?:the )?production\b|\bSQLite\b))(?=(?:(?!\n## )[\s\S])*?\b(?:2|two)\b)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
