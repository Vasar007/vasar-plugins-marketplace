---
type: regex
pattern: '^## Notes\b(?=(?:(?!\n## )[\s\S])*?#77\b)(?=(?:(?!\n## )[\s\S])*?\bcounter\b)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
