---
type: regex
pattern: '\tpush$'
flags: m
match: "count:1"
target: { source: file, path: .remote/origin.git/logs/refs/heads/feature/paging }
---
