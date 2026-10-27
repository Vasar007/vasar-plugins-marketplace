---
type: regex
pattern: '(?=[\s\S]*\b30\b)(?=[\s\S]*\b22\b)(?=[\s\S]*bandwidth)(?=[\s\S]*KB/s)(?=[\s\S]*unknown directive)(?=[\s\S]*exclude)(?=[\s\S]*include)'
target: { source: file, path: docs/snapsync.conf.md }
arm: both
---
