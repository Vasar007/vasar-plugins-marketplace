---
type: regex
pattern: '(?=[\s\S]*(?:libssh[^\n]*(?:\n[^\n]*){0,3}0\.10|0\.10[^\n]*(?:\n[^\n]*){0,3}libssh))(?=[\s\S]*(?:make install[^\n]*(?:\n[^\n]*){0,3}/usr/local/bin|/usr/local/bin[^\n]*(?:\n[^\n]*){0,3}make install))(?=[\s\S]*(?:-k\b[^\n]*(?:\n[^\n]*){0,3}\b30\b|\b30\b[^\n]*(?:\n[^\n]*){0,3}-k\b))'
target: { source: file, path: README.md }
arm: both
---
