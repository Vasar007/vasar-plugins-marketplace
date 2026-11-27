---
type: regex
pattern: '(?:rule[ -]candidate|candidate rule|draft rule)[^\n]{0,300}9204|9204[^\n]{0,300}(?:rule[ -]candidate|candidate rule|draft rule)'
flags: i
match: not_contains
target: last_message
---
