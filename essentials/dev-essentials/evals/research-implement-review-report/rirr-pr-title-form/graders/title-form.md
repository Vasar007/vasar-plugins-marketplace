---
type: regex
pattern: '"tool":"(?:[\w-]*__)?create_pull_request"[^\n]*?"title":"(?:feat|fix|refactor|docs|test|chore)\([\w-]+\): [^"\n]'
target: mock_calls
---
