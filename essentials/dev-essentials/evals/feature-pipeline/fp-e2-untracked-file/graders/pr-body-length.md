---
type: regex
pattern: '"tool":"(?:[\w-]*__)?create_pull_request"[^\n]*?"body":"(?:[^"\\\n]|\\.){1,1000}?(?:(?:\\n)+[^"\\\n]*Claude Code[^"\\\n]*)?(?:\\n)*"'
target: mock_calls
---
