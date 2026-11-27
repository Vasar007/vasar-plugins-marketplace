---
type: regex
pattern: '^## UI changes\b(?=(?:(?!\n## )[\s\S])*?^[ \t]*\|[^\n]*\bBefore\b[^\n]*\bAfter\b)(?=(?:(?!\n## )[\s\S])*?0b6f1c2e-5d4a-4e8b-9f3a-2c7d8e9a1b01)(?=(?:(?!\n## )[\s\S])*?7e2d9a4b-1c3f-4a6e-8b5d-9f0e1a2b3c04)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
