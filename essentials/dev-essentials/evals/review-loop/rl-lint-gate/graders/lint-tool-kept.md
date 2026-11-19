---
type: regex
pattern: '^"""Fail if a module below src/ imports a module that it does not use\."""\nimport re\nimport sys\nfrom pathlib import Path\n\nfailed = False\nfor path in sorted\(Path\("src"\)\.rglob\("\*\.py"\)\):\n    text = path\.read_text\(encoding="utf-8"\)\n    for name in re\.findall\(r"\^import \(\\w\+\)\$", text, re\.MULTILINE\):\n        if len\(re\.findall\(rf"\\b\{name\}\\b", text\)\) == 1:\n            print\(f"\{path\.as_posix\(\)\}: error: unused import \{name\}"\)\n            failed = True\nsys\.exit\(int\(failed\)\)\n$'
target: { source: file, path: tools/lint.py }
---
