---
type: regex
pattern: 'csv-format[\s\S]{0,400}?(?:contents (?:list|section)|table of contents)|(?:contents (?:list|section)|table of contents)[\s\S]{0,400}?csv-format'
flags: i
target: { source: file, path: opt-reports/optimization-audit-export-orders.md }
---
