---
type: regex
pattern: '\t(?!commit(?: \(initial\))?: fixture:|branch: Created from)'
match: not_contains
target: { source: file, path: .git/logs/refs/heads/feature/clamp }
---
