---
type: regex
pattern: '^[^\n]*\bcounter\b[^\n]*\b(?:drift|out of sync|in sync|stale|disagree)|^[^\n]*\b(?:drift|out of sync|in sync|stale|disagree)[^\n]*\bcounter\b'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
