---
type: regex
pattern: 'File:\s*\x60?(?:\S*/)?src/Inventory/AccessPolicy\.cs:\d+(?:(?!\*\*\[|\bFile:)[\s\S]){0,600}?(?:null user|(?:user|principal) (?:is|==|being) null|missing user|anonymous|unauthenticated|bypass|authori[sz]ation|access control|CWE-(?:284|285|287|306|862|863))'
flags: i
target: trace
---
