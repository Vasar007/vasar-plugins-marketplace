---
type: regex
pattern: 'print\(f"\{path\.as_posix\(\)\}: error: unused import \{name\}"\)\n            failed = True\nsys\.exit\(int\(failed\)\)\n'
target: { source: file, path: tools/lint.py }
---
