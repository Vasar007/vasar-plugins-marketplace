---
type: regex
pattern: 'Location: [^\n]*billing/invoice\.py:(?:10|11|12|13|14)\b[^\n]*(?:\n[^\n]*){0,6}Verdict: (?:Confirmed|Unconfirmed)'
target: { source: file, path: reports/bug-hunt-report.md }
---
