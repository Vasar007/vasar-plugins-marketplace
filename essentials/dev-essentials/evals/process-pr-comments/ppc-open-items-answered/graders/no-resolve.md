---
type: regex
pattern: '"tool":"(?:[\w-]*__)?pull_request_review_write"'
match: not_contains
target: mock_calls
---
