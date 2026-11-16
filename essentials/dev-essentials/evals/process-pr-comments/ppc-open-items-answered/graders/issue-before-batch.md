---
type: regex
pattern: '"tool":"(?:\w*__)?add_reply_to_pull_request_comment"[\s\S]*"tool":"(?:\w*__)?issue_write"'
match: not_contains
target: mock_calls
---
