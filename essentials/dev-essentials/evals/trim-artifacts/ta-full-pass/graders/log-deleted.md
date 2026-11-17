---
type: regex
pattern: '^notes/[^\n]*session-log-2026-10'
flags: m
match: not_contains
target: { source: file, path: trim-listing.txt }
---
