---
type: regex
pattern: 'if not layout\.is_file\(\):\n        print\("error: the docs theme is missing\. Clone the pager-docs-theme repository next to this repository\.", file=sys\.stderr\)\n        return 1\n'
target: { source: file, path: tools/build_docs.py }
---
