---
type: regex
pattern: '"tool":"(?:[\w-]*__)?pull_request_read"[^\n]*?"method":"get_check_runs"[\s\S]*"tool":"(?:[\w-]*__)?merge_pull_request"'
target: mock_calls
---
