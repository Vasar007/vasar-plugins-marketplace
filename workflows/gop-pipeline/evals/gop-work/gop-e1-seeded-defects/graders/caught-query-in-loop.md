---
type: regex
pattern: 'File:\s*\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!\*\*\[|\bFile:)[\s\S]){0,600}?(?:N\+1|QueryMany|quer(?:y|ies) (?:in|inside|within) (?:a|the|each) loop|quer(?:y|ies) (?:per|for each) (?:sku|item|iteration)|call(?:s|ed)? (?:\w+ ){0,3}(?:in|inside|within) (?:a|the|each) loop)'
flags: i
target: trace
---
