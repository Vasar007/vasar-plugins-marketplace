---
type: regex
pattern: '^## Testing\b(?:(?!\n## )[\s\S])*?(?:unittest discover|\b3 tests\b|\bOK\b|\bpassed\b)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
