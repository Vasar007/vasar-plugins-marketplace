---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/InventoryOptions\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:secret|credential|hard-?coded|api key)|(?:secret|credential|hard-?coded|api key)(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/InventoryOptions\.cs:\d+)|(?:(?:(?:ApiKey|inv-key-0042-local)(?:(?!\\n)[^\n]){0,300}?(?:secret|credential|hard-?coded|api key)|(?:secret|credential|hard-?coded|api key)(?:(?!\\n)[^\n]){0,300}?(?:ApiKey|inv-key-0042-local))(?=[^\n]{0,6000}?QUESTIONS:\\n[^\n]{0,3000}?Recommended:)|QUESTIONS:\\n[^\n]{0,3000}?Recommended:[^\n]{0,6000}?(?:(?:ApiKey|inv-key-0042-local)(?:(?!\\n)[^\n]){0,300}?(?:secret|credential|hard-?coded|api key)|(?:secret|credential|hard-?coded|api key)(?:(?!\\n)[^\n]){0,300}?(?:ApiKey|inv-key-0042-local)))'
flags: i
target: trace
---
