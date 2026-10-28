---
type: regex
pattern: '(?=[\s\S]*-b\b)(?=[\s\S]*src/main\.c)(?=[\s\S]*src/conf\.c)(?=[\s\S]*src/xfer\.c)(?=[\s\S]*make test)(?=[\s\S]*1000000)(?=[\s\S]*getopt)'
target: { source: file, path: plan.md }
arm: both
---
