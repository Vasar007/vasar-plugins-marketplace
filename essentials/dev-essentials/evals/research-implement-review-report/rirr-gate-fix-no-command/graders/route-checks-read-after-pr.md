---
type: regex
pattern: '"tool":"(?:[\w-]*__)?create_pull_request"[\s\S]*"tool":"(?:[\w-]*__)?pull_request_read"[^\n]*?"method":"get_check_runs"'
target: mock_calls
---
