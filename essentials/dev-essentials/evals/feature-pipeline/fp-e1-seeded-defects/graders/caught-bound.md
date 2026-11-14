---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:off-by-one|off by one|out of range|out-of-range|IndexOutOfRange|<= ?\w*\.?Length|upper bound)|(?:off-by-one|off by one|out of range|out-of-range|IndexOutOfRange|<= ?\w*\.?Length|upper bound)(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/StockQuery\.cs:\d+)|(?:(?:(?:FindQuantities)(?:(?!\\n)[^\n]){0,300}?(?:off-by-one|off\sby\sone|IndexOutOfRange|out\sof\srange|out-of-range|upper\sbound|past\sthe\send)|(?:off-by-one|off\sby\sone|IndexOutOfRange|out\sof\srange|out-of-range|upper\sbound|past\sthe\send)(?:(?!\\n)[^\n]){0,300}?(?:FindQuantities))(?=[^\n]{0,6000}?QUESTIONS:\\n[^\n]{0,3000}?Recommended:)|QUESTIONS:\\n[^\n]{0,3000}?Recommended:[^\n]{0,6000}?(?:(?:FindQuantities)(?:(?!\\n)[^\n]){0,300}?(?:off-by-one|off\sby\sone|IndexOutOfRange|out\sof\srange|out-of-range|upper\sbound|past\sthe\send)|(?:off-by-one|off\sby\sone|IndexOutOfRange|out\sof\srange|out-of-range|upper\sbound|past\sthe\send)(?:(?!\\n)[^\n]){0,300}?(?:FindQuantities)))'
flags: i
target: trace
---
