---
type: regex
pattern: '(?=[\s\S]*(?:-k\b[^\n]*(?:\n[^\n]*){0,3}\b30\b|\b30\b[^\n]*(?:\n[^\n]*){0,3}-k\b))(?=[\s\S]*(?:-k\b[^\n]*(?:\n[^\n]*){0,3}\b365\b|\b365\b[^\n]*(?:\n[^\n]*){0,3}-k\b))(?=[\s\S]*(?:-c\b[^\n]*(?:\n[^\n]*){0,3}/etc/snapsync\.conf|/etc/snapsync\.conf[^\n]*(?:\n[^\n]*){0,3}-c\b))(?=[\s\S]*(?:-p\b[^\n]*(?:\n[^\n]*){0,3}\b22\b|\b22\b[^\n]*(?:\n[^\n]*){0,3}-p\b))'
target: { source: file, path: docs/cli.md }
arm: both
---
