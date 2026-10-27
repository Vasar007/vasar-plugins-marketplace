---
type: regex
pattern: '(?=[\s\S]*(?:keep[^\n]*(?:\n[^\n]*){0,3}\b30\b|\b30\b[^\n]*(?:\n[^\n]*){0,3}keep))(?=[\s\S]*(?:port[^\n]*(?:\n[^\n]*){0,3}\b22\b|\b22\b[^\n]*(?:\n[^\n]*){0,3}port))(?=[\s\S]*(?:bandwidth[^\n]*(?:\n[^\n]*){0,3}KB/s|KB/s[^\n]*(?:\n[^\n]*){0,3}bandwidth))'
target: { source: file, path: docs/snapsync.conf.md }
arm: both
---
