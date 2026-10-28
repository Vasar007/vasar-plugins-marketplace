---
type: regex
pattern: '(?=[\s\S]*ENOSPC)(?=[\s\S]*\b212\b)(?=[\s\S]*src/xfer\.c)(?=[\s\S]*tests/test_full\.c)(?=[\s\S]*docs/cli\.md)(?=[\s\S]*-k\b)(?=[\s\S]*\b3\b)'
target: { source: file, path: pr.md }
arm: both
---
