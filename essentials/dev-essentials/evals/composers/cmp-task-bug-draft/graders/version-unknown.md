---
type: regex
pattern: '\b(?:version|commit)\b[^\n]{0,80}\b(?:unknown|not (?:given|known|specified|provided|stated)|n/a)\b|\b(?:unknown|not (?:given|known|specified|provided|stated))\b[^\n]{0,40}\b(?:version|commit)\b'
flags: i
target: { source: file, path: notes/Tasks/task-report-email.md }
---
