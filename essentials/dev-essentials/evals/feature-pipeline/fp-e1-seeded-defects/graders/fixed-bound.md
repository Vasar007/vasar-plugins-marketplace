---
type: regex
pattern: 'for\s*\([^)]*<=\s*\w+\.Length'
match: not_contains
target: { source: file, path: src/Inventory/StockQuery.cs }
---
