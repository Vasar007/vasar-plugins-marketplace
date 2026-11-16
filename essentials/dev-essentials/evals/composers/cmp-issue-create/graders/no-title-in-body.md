---
type: regex
pattern: '"tool":"\w*issue_write"[^\n]{0,1500}?body\\?"\s*:\s*\\?"#[ \t]'
match: not_contains
target: mock_calls
---
