---
type: regex
pattern: '^## Why\b(?:(?!\n## )[\s\S])*?(?:invoic\w* (?:report|job)|report job|time[sd]?[ -]?out)'
flags: mi
target: { source: file, path: Notes/PRs/PR-user-tasks-12-customer-index.md }
---
