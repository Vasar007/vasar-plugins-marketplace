---
type: regex
pattern: '^[^\n]*\bPostgres(?:QL)?\b[^\n]*(?:\bnot\b|\bnever\b|\bnobody\b|\buntested\b|\bno\b)|^[^\n]*(?:\bnot\b|\bnever\b|\bnobody\b|\buntested\b|\bno\b)[^\n]*\bPostgres(?:QL)?\b'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
