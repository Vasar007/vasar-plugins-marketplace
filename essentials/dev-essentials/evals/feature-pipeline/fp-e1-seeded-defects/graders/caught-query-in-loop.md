---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:N\+1|QueryMany|\bper[- ]sku\b|\bfor (?:each|every) sku\b|round[- ]trips?\b|quer(?:y|ies) (?:per|for (?:each|every)) (?:sku|item|iteration|element)\b|quer(?:y|ies|ying)\b[^\n]{0,40}?\b(?:in|inside|within) (?:a|the|each) loop|call(?:s|ed)? (?:\w+ ){0,3}(?:in|inside|within) (?:a|the|each) loop)|(?:N\+1|QueryMany|\bper[- ]sku\b|\bfor (?:each|every) sku\b|round[- ]trips?\b|quer(?:y|ies) (?:per|for (?:each|every)) (?:sku|item|iteration|element)\b|quer(?:y|ies|ying)\b[^\n]{0,40}?\b(?:in|inside|within) (?:a|the|each) loop|call(?:s|ed)? (?:\w+ ){0,3}(?:in|inside|within) (?:a|the|each) loop)(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+)'
flags: i
target: trace
---
