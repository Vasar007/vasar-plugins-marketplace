---
type: regex
pattern: '^(?![\s\S]*push and pull request only)(?=[\s\S]*\b(?:repo(?:s|sitor(?:y|ies))?|upstream|origin|remotes?|fork)\b)[\s\S]*\?'
flags: i
target: last_message
---
