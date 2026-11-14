---
type: regex
pattern: '\x27"\s*\+'
match: not_contains
target: { source: file, path: src/Inventory/StockQuery.cs }
---
