---
type: regex
pattern: '"tool":"(?:\w*__)?pull_request_review_write"[^\n]*?"method":"resolve_thread"'
match: not_contains
target: mock_calls
---
