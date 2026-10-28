---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?src/Inventory/AccessPolicy\.cs:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:null\s(?:\w+\s)?user|null\sStockUser|(?:user|principal) (?:is|==|being) null|missing user|anonymous|unauthenticated|bypass|authori[sz]ation|access control|CWE-(?:284|285|287|306|862|863))|(?:null\s(?:\w+\s)?user|null\sStockUser|(?:user|principal) (?:is|==|being) null|missing user|anonymous|unauthenticated|bypass|authori[sz]ation|access control|CWE-(?:284|285|287|306|862|863))(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?src/Inventory/AccessPolicy\.cs:\d+)'
flags: i
target: trace
---
