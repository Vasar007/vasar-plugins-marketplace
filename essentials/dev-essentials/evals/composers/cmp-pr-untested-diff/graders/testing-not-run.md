---
type: regex
pattern: '^## Testing\b(?:(?!\n## )[\s\S])*?(?:(?:\bnot|\bnever|n[\x27’]t)(?: been| yet)* (?:run|executed)\b|\bno test run)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
