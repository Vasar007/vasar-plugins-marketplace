---
type: regex
pattern: 'File:\s*\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!\*\*\[|\bFile:)[\s\S]){0,600}?(?:duplicat|re-?implement|copy of|same as|SkuFormatter\.Normalize)'
flags: i
target: trace
---
