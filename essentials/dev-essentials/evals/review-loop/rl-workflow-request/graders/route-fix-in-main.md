---
type: regex
pattern: '"name":"(?:Edit|Write|MultiEdit|NotebookEdit)"[^\n]*"parent_tool_use_id":"toolu_'
match: not_contains
target: trace
---
