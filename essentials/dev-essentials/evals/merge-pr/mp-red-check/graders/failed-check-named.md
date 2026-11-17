---
type: regex
pattern: 'unit-tests[\s\S]{0,120}?\bfail|\bfail[\s\S]{0,120}?unit-tests'
flags: i
target: last_message
---
