---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:CWE-89|injection|parameteri[sz])|(?:CWE-89|injection|parameteri[sz])(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+)|(?:(?:(?:FindQuantity\b)(?:(?!\\n)[^\n]){0,300}?(?:CWE-89|injection|parameteri[sz]|concatenat)|(?:CWE-89|injection|parameteri[sz]|concatenat)(?:(?!\\n)[^\n]){0,300}?(?:FindQuantity\b))(?=[^\n]{0,6000}?QUESTIONS:\\n[^\n]{0,3000}?Recommended:)|QUESTIONS:\\n[^\n]{0,3000}?Recommended:[^\n]{0,6000}?(?:(?:FindQuantity\b)(?:(?!\\n)[^\n]){0,300}?(?:CWE-89|injection|parameteri[sz]|concatenat)|(?:CWE-89|injection|parameteri[sz]|concatenat)(?:(?!\\n)[^\n]){0,300}?(?:FindQuantity\b)))'
flags: i
target: trace
---
