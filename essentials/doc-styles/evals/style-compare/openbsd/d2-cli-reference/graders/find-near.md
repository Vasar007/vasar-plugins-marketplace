---
type: regex
pattern: '(?=[\s\S]*(?:-k\b[^\n]*(?:\n[^\n]*){0,5}\b30\b|\b30\b[^\n]*(?:\n[^\n]*){0,5}-k\b))(?=[\s\S]*(?:-k\b[^\n]*(?:\n[^\n]*){0,5}\b365\b|\b365\b[^\n]*(?:\n[^\n]*){0,5}-k\b))(?=[\s\S]*(?:-c\b[^\n]*(?:\n[^\n]*){0,5}/etc/snapsync\.conf|/etc/snapsync\.conf[^\n]*(?:\n[^\n]*){0,5}-c\b))(?=[\s\S]*(?:-p\b[^\n]*(?:\n[^\n]*){0,5}\b22\b|\b22\b[^\n]*(?:\n[^\n]*){0,5}-p\b))'
target: { source: file, path: docs/cli.md }
arm: both
---
