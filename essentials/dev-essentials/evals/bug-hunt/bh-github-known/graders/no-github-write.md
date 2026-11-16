---
type: regex
pattern: '"tool":"(?:[\w-]*__)?(?:issue_write|add_issue_comment|create_\w*)"'
match: not_contains
target: mock_calls
---
