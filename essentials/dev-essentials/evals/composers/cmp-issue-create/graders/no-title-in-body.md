---
type: regex
pattern: 'issue_write[\s\S]{0,1500}?body\\?"\s*:\s*\\?"#[ \t]'
match: not_contains
target: mock_calls
---
