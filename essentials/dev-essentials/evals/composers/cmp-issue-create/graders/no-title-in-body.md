---
type: regex
pattern: '"tool":"(?:[\w-]*__)?issue_write"(?![^\n]{0,1500}?body\\?"[^\S\n]*:[^\S\n]*\\?"#[ \t])'
target: mock_calls
---
