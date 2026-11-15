---
type: regex
pattern: '\b(?:SELECT|WHERE|FROM|AND|OR|IN|VALUES|SET)\b[^\n]*?(?:\x27"\s*\+|\x27\{)'
match: not_contains
target: { source: file, path: src/Inventory/StockQuery.cs }
---
