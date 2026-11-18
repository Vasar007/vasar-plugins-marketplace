---
type: regex
pattern: '"tool":"(?:[\w-]*__)?merge_pull_request"[^\n]*?"commit_message":"Add paging to the order list'
match: not_contains
target: mock_calls
---
