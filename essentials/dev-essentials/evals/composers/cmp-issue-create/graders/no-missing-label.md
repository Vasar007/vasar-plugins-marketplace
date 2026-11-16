---
type: regex
pattern: 'issue_write[\s\S]{0,4000}?labels[^\]]{0,10}\[[^\]]*performance'
match: not_contains
target: mock_calls
---
