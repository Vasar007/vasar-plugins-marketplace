---
type: regex
pattern: '^## Testing\b(?:(?!\n## )[\s\S])*?Not confirmed:[^\n]*\bPostgres'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
