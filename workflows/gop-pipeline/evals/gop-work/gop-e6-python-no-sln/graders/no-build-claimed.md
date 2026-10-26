---
type: regex
pattern: '\b(?:no|skipped|skip|not run|without)\b[^\n]{0,60}\b(?:build|tests?|solution|\.sln)\b'
flags: i
target: last_message
---
