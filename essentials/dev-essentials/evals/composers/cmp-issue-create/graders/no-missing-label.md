---
type: regex
pattern: '"tool":"(?:\w*__)?issue_write"[^\n]{0,4000}?labels[^\]\n]{0,10}\[[^\]\n]*performance'
match: not_contains
target: mock_calls
---
