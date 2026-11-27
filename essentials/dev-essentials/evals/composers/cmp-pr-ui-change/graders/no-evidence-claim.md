---
type: regex
pattern: '^(?![^\n]*(?:not confirmed|\bnot\b|\bno\b|missing|pending|to be added|\btodo\b|\btbd\b|\badd\b|\bupload\b))[^\n]*(?:\b(?:screenshots?|images?|videos?|recordings?)\b[^\n]*\b(?:below|above|attached|included|shows?)\b|\b(?:see|attached)\b[^\n]*\b(?:screenshots?|images?|videos?|recordings?)\b)'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
