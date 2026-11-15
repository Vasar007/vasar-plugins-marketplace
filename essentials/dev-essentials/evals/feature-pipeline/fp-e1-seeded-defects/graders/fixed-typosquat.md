---
type: regex
pattern: 'Newtonsoft\.Jsonn'
match: not_contains
target: { source: file, path: Directory.Packages.props }
---
