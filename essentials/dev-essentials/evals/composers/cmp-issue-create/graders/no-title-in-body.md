---
type: regex
pattern: '"tool":"(?:[\w-]*__)?issue_write"[^\n]{0,1500}?body\\?"[^\S\n]*:[^\S\n]*\\?"#[ \t]'
match: not_contains
target: mock_calls
---
