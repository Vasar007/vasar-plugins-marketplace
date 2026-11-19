---
type: regex
pattern: '"command":"(?:[^"\\]|\\.)*\bgit\s(?:(?:[^"\\&\x3b|]|\\.)*?\s)?show\s+(?:\\")?(?:[\w./-]*\bmain|[0-9a-f]{7,40}|\$\{?\w+\}?|\$\(git merge-base[^)]*\))(?:\\")?:(?:\./)?CLAUDE\.md(?:[^"\\]|\\.)*"[^\n]*"parent_tool_use_id":null'
target: trace
---
