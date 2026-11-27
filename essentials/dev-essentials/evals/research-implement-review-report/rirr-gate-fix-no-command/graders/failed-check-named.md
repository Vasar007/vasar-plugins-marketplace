---
type: regex
pattern: '\blint\b[\s\S]{0,160}?(?:\bfail|\bred\b|\bnot pass)|(?:\bfail|\bred\b|\bnot pass)[\s\S]{0,160}?\blint\b'
flags: i
target: last_message
---
