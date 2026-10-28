---
type: regex
pattern: '(?=[\s\S]*/etc/snapsync\.conf)(?=[\s\S]*\b365\b)(?=[\s\S]*SNAPSYNC_SSH)(?=[\s\S]*/var/db/snapsync/state)(?=[\s\S]*2 GiB)(?=[\s\S]*\b3\b)'
target: { source: file, path: docs/cli.md }
arm: both
---
