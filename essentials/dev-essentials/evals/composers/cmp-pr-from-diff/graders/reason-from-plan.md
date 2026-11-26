---
type: regex
pattern: '^## Why\b(?:(?!\n## )[\s\S])*?(?:invoic\w*[ -](?:report|job|run)|report job|time[sd]?[ -]?out)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
