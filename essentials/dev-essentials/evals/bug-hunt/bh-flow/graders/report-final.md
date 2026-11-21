---
type: regex
pattern: '\nFindings: \d+\.[\s\S]*\n### For the owner''s review\n'
target: { source: file, path: reports/bug-hunt-report.md }
---
