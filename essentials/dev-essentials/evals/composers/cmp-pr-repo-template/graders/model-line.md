---
type: regex
pattern: '^## Evidence\b[\s\S]*^[^\n]*(?:Claude Code[^\n]*\b(?:Opus|Sonnet|Haiku|Fable)\b|\b(?:Opus|Sonnet|Haiku|Fable)\b[^\n]*Claude Code)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
