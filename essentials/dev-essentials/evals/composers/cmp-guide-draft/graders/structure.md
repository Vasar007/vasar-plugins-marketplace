---
type: regex
pattern: '^\s*# \S[^\n]*\n(?:[\s\S]*\n## \S|(?![\s\S]*\n#{2,6}[ \t])[\s\S]*\n[ \t]*1\. \S)'
target: { source: file, path: docs/drafts/run-tests-locally.md }
---
