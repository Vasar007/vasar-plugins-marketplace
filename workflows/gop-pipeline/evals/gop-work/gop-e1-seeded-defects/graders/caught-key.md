---
type: regex
pattern: 'File:\s*\x60?(?:\S*/)?src/Inventory/InventoryOptions\.cs:\d+(?:(?!\*\*\[|\bFile:)[\s\S]){0,600}?(?:secret|credential|hard-?coded|api key)'
flags: i
target: trace
---
