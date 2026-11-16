---
type: regex
pattern: '"tool":"(?:[\w-]*__)?issue_write"[^\n]{0,4000}?"labels":\[[^\]\n]*"performance"'
match: not_contains
target: mock_calls
---
