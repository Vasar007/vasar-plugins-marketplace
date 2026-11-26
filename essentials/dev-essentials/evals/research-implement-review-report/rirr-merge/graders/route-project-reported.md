---
type: regex
pattern: '\bprojects?\b[^\n.]{0,200}\b(?:not|unable|\w+n.t|failed|error|skipped|unknown)\b|\b(?:not|unable|\w+n.t|failed|error|skipped|unknown)\b[^\n.]{0,200}\bprojects?\b|\bno projects? set\b'
flags: i
target: last_message
---
