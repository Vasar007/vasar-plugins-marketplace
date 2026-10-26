---
type: regex
pattern: 'Location: [^\n]*inventory/stock\.py[^\n]*(?:\n[^\n]*){0,6}Verdict: Confirmed'
match: not_contains
target: { source: file, path: reports/bug-hunt-report.md }
---
