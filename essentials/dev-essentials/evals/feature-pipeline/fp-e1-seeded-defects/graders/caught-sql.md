---
type: regex
pattern: '- \[ \](?!(?:(?!- \[ \]|\\n##|\\n\\n|Recommendation:|Fix:)(?:[^"\\\n]|\\.)){0,1600}?(?:\bno\s(?:SQL\s)?injection\b|\bnot\s(?:open|vulnerable|exposed)\sto\s(?:SQL\s)?injection\b))(?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:CWE-89|injection|parameteri[sz])|(?:CWE-89|injection|parameteri[sz])(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+)|(?:"subtype":"task_notification"[^\n]{0,2000}?"summary":"(?=(?:[^"\\\n]|\\.){0,30000}","usage":\{)|"agentType":"[^"\n]{0,100}"[^\n]{0,20000}?\{"type":"text","text":")(?=(?:[^"\\\n]|\\.){0,30000}?(?:(?<=:")|\\n)\x20{0,8}QUESTIONS:\\n(?!(?:\x20{0,8}\\n){0,2}\x20{0,8}1\.\s<question>)(?:[^"\\\n]|\\.){0,4000}?Recommended:)(?:[^"\\\n]|\\.){0,30000}?(?:(?:FindQuantity\b)(?:[^"\\\n]|\\[^n]){0,300}?(?:CWE-89|injection|parameteri[sz]|concatenat)|(?:CWE-89|injection|parameteri[sz]|concatenat)(?:[^"\\\n]|\\[^n]){0,300}?(?:FindQuantity\b))'
flags: i
target: trace
---
