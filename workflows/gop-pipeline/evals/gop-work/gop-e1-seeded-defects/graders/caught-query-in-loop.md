---
type: regex
pattern: 'File:\s*\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!\*\*\[|\bFile:)[\s\S]){0,600}?(?:N\+1|QueryMany|loop|for each sku|per sku)'
flags: i
target: trace
---
