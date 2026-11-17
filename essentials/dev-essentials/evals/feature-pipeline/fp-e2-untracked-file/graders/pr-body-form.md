---
type: regex
pattern: '"tool":"(?:[\w-]*__)?create_pull_request"[^\n]*?"body":"(?:(?!#+ )(?:(?!\\n#+ )[^\n])*?\\n)?## What\\n(?:(?!\\n#+ )[^\n])*\\n## Why\\n(?:(?!\\n#+ )[^\n])*\\n## Changes\\n'
target: mock_calls
---
