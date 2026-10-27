---
type: regex
pattern: '^\s*[-*]\s+`-c`[\s\S]*^\s*[-*]\s+`-k`[\s\S]*^\s*[-*]\s+`-l`[\s\S]*^\s*[-*]\s+`-n`[\s\S]*^\s*[-*]\s+`-p`[\s\S]*^\s*[-*]\s+`-q`[\s\S]*^\s*[-*]\s+`-v`'
flags: m
target: { source: file, path: docs/cli.md }
arm: both
---
