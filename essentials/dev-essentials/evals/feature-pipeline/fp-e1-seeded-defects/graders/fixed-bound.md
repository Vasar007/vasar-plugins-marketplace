---
type: regex
pattern: '\b(?:for|while)\s*\([^)]*<=\s*\w+\.Length\b(?!\s*-\s*1\b)'
match: not_contains
target: { source: file, path: src/Inventory/StockQuery.cs }
---
