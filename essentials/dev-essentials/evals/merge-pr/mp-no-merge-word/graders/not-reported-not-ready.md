---
type: regex
pattern: '(?:\bnot|n.t)[ \t*_]+(?:(?:yet|quite|currently|really|fully)[ \t*_]+)?ready\b'
flags: i
match: not_contains
target: last_message
---
