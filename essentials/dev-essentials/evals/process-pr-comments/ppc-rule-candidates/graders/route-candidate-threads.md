---
type: regex
pattern: '(?:rule[ -]candidates?|candidate rules?|draft rule)[\s\S]{0,300}^(?=[^\n]*9201)(?=[^\n]*9202)(?=[^\n]*9203)|^(?=[^\n]*9201)(?=[^\n]*9202)(?=[^\n]*9203)[^\n]*(?:\n[^\n]*){0,2}?(?:rule[ -]candidates?|candidate rules?|draft rule)'
flags: im
target: last_message
---
