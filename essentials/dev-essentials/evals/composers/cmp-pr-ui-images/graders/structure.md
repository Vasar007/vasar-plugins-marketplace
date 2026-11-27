---
type: regex
pattern: '^\s*## What[ \t\r]*(?:\n(?!#{1,6} )[^\n]*)*\n## Why[ \t\r]*(?:\n(?!#{1,6} )[^\n]*)*\n## Changes[ \t\r]*\n[\s\S]*\n## Testing\b'
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
