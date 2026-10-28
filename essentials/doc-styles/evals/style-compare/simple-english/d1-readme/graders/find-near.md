---
type: regex
pattern: '(?=[\s\S]*(?:libssh[^\n]*(?:\n[^\n]*){0,5}0\.10|0\.10[^\n]*(?:\n[^\n]*){0,5}libssh))(?=[\s\S]*(?:make install[^\n]*(?:\n[^\n]*){0,5}/usr/local/bin|/usr/local/bin[^\n]*(?:\n[^\n]*){0,5}make install))(?=[\s\S]*(?:-k\b[^\n]*(?:\n[^\n]*){0,5}\b30\b|\b30\b[^\n]*(?:\n[^\n]*){0,5}-k\b))'
target: { source: file, path: README.md }
arm: both
---
