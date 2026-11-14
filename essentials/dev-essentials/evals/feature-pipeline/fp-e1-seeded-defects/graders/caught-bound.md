---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:off-by-one|off by one|out of range|out-of-range|IndexOutOfRange|<= ?\w*\.?Length|upper bound)|(?:off-by-one|off by one|out of range|out-of-range|IndexOutOfRange|<= ?\w*\.?Length|upper bound)(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+)|(?:"subtype":"task_notification"[^\n]{0,2000}?"summary":"|"agentType":"[^"\n]{0,100}"[^\n]{0,20000}?\{"type":"text","text":")(?=(?:[^"\\\n]|\\.){0,30000}?(?:(?<=:")|\\n)\x20{0,8}QUESTIONS:\\n(?!\x20{0,8}1\.\s<question>)(?:[^"\\\n]|\\.){0,4000}?Recommended:)(?:[^"\\\n]|\\.){0,30000}?(?:(?:FindQuantities)(?:[^"\\\n]|\\[^n]){0,300}?(?:off-by-one|off\sby\sone|IndexOutOfRange|out\sof\srange|out-of-range|upper\sbound|past\sthe\send)|(?:off-by-one|off\sby\sone|IndexOutOfRange|out\sof\srange|out-of-range|upper\sbound|past\sthe\send)(?:[^"\\\n]|\\[^n]){0,300}?(?:FindQuantities))'
flags: i
target: trace
---
