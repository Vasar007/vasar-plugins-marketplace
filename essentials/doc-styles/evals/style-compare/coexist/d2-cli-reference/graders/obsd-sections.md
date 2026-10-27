---
type: regex
pattern: '^## SYNOPSIS$[\s\S]*^## DESCRIPTION$'
flags: m
target: { source: file, path: docs/cli.md }
arm: both
---
