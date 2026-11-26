---
type: regex
pattern: '\bprojects?\b[^\n.]{0,200}\b(?:not|unable|can.t|failed|error|skipped|unknown)\b|\b(?:not|unable|can.t|failed|error|skipped|unknown)\b[^\n.]{0,200}\bprojects?\b'
flags: i
target: last_message
---
