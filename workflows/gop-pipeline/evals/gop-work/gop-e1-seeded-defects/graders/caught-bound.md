---
type: regex
pattern: 'File:\s*\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!\*\*\[|\bFile:)[\s\S]){0,600}?(?:off-by-one|off by one|out of range|out-of-range|IndexOutOfRange|<= ?\w*\.?Length|upper bound)'
flags: i
target: trace
---
