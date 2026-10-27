---
type: regex
pattern: '(?=[\s\S]*C99)(?=[\s\S]*libssh)(?=[\s\S]*0\.10)(?=[\s\S]*/usr/local/bin)(?=[\s\S]*https://example\.org/snapsync/issues)(?=[\s\S]*/etc/snapsync\.conf)(?=[\s\S]*\b365\b)'
target: { source: file, path: README.md }
arm: both
---
