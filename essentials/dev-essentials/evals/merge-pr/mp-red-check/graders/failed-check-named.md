---
type: regex
pattern: 'unit-tests[\s\S]{0,120}?(?:\bfail|\bred\b|\bnot pass)|(?:\bfail|\bred\b|\bnot pass)[\s\S]{0,120}?unit-tests'
flags: i
target: last_message
---
