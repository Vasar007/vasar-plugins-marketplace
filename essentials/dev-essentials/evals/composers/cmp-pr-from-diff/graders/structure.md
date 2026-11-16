---
type: regex
pattern: '^\s*## What[ \t]*(?:\n(?!## )[^\n]*)*\n## Why[ \t]*(?:\n(?!## )[^\n]*)*\n## Changes[ \t]*\n[\s\S]*\n## Testing\b'
target: { source: file, path: Notes/PRs/PR-user-tasks-12-customer-index.md }
---
