---
type: regex
pattern: '^"""Page labels of the upstream package\."""\nimport os\n\n\ndef page_label\(page\):\n    """Return the label of a page\."""\n    return f"page \{page\}"\n$'
target: { source: file, path: src/vendor/legacy.py }
---
