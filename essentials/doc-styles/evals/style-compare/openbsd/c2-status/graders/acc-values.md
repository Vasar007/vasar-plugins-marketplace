---
type: regex
pattern: '(?=[\s\S]*2026-11-03)(?=[\s\S]*2026-11-06)(?=[\s\S]*2026-10-30)(?=[\s\S]*Dana)(?=[\s\S]*(?:\b(?:3|three) of (?:the )?(?:4|four)\b|\b(?:other|remaining) (?:3|three)\b|\bfixed (?:3|three) blockers))(?=[\s\S]*FreeBSD 14)'
flags: i
target: last_message
arm: both
---
