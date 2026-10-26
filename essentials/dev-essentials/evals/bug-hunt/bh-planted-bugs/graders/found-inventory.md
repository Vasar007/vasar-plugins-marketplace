---
type: regex
pattern: 'Location: [^\n]*inventory/cache\.py:(?:6|7|8|9|10)\b[^\n]*(?:\n[^\n]*){0,6}Verdict: (?:Confirmed|Unconfirmed)'
target: { source: file, path: reports/bug-hunt-report.md }
---
