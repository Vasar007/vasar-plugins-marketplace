---
type: regex
pattern: '\broute\b[^\n]{0,4}:[^\n]*\b(?:main (?:loop|session)|context|parallel work|independent view|tool isolation|review(?:er|-loop| loop)?)\b'
flags: i
target: last_message
---
