---
type: regex
pattern: '(?=[\s\S]*\b3\b)(?=[\s\S]*-k\b)(?=[\s\S]*free)(?=[\s\S]*oldest)(?=[\s\S]*(?:again|re-?run|retry))'
flags: i
target: last_message
arm: both
---
