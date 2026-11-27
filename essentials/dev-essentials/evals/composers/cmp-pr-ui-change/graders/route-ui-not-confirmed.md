---
type: regex
pattern: '^## UI changes\b(?=(?:(?!\n## )[\s\S])*?Not confirmed:)(?=(?:(?!\n## )[\s\S])*?\bbefore\b)(?=(?:(?!\n## )[\s\S])*?\bafter\b)(?=(?:(?!\n## )[\s\S])*?\b(?:videos?|recordings?)\b)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
