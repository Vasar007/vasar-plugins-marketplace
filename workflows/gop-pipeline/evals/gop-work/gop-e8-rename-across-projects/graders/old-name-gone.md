---
type: regex
pattern: 'GetQuantity\('
match: not_contains
target: { source: file, path: src/Inventory.Reports/ReportBuilder.cs }
---
