---
type: regex
pattern: '"tool":"(?:[\w-]*__)?(?:list_pull_requests|create_pull_request)"'
match: not_contains
target: mock_calls
---
