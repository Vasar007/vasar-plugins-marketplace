---
type: regex
pattern: 'old-retry-notes[^\n]*(?:unlinked|not linked|no (?:step|link)|orphan|delete|remove)|(?:unlinked|not linked|no (?:step|link)|orphan|delete|remove)[^\n]*old-retry-notes'
flags: i
target: { source: file, path: opt-reports/optimization-audit-export-orders.md }
---
