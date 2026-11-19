---
type: regex
pattern: '"name":"Agent","input":\{[^\n]*?\b(?:(?:Blocker|Critical|High|Medium|Low|Nit)\W{1,6}(?:APPLY|PARTIAL|REJECT)|(?:APPLY|PARTIAL|REJECT)\W{1,6}(?:Blocker|Critical|High|Medium|Low|Nit))\b[^\n]*"parent_tool_use_id":null'
target: trace
---
