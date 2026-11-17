---
type: regex
pattern: '^notes/archive(?:/|$)'
flags: m
match: not_contains
target: { source: file, path: trim-listing.txt }
---
