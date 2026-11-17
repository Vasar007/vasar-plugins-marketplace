---
type: regex
pattern: '"tool":"(?:[\w-]*__)?create_pull_request"[^\n]*?"body":"(?:[^"\\\n]|\\.){1,1000}"'
target: mock_calls
---
