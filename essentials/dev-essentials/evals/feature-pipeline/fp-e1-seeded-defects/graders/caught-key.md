---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/InventoryOptions\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:secret|credential|hard-?coded|api key)|(?:secret|credential|hard-?coded|api key)(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/InventoryOptions\.cs:\d+)|(?:"subtype":"task_notification"[^\n]{0,2000}?"summary":"|"agentType":"[^"\n]{0,100}"[^\n]{0,20000}?\{"type":"text","text":")(?=(?:[^"\\\n]|\\.){0,30000}?(?:(?<=:")|\\n)\x20{0,8}QUESTIONS:\\n(?!\x20{0,8}1\.\s<question>)(?:[^"\\\n]|\\.){0,4000}?Recommended:)(?:[^"\\\n]|\\.){0,30000}?(?:(?:ApiKey|inv-key-0042-local)(?:[^"\\\n]|\\[^n]){0,300}?(?:secret|credential|hard-?coded|api key)|(?:secret|credential|hard-?coded|api key)(?:[^"\\\n]|\\[^n]){0,300}?(?:ApiKey|inv-key-0042-local))'
flags: i
target: trace
---
