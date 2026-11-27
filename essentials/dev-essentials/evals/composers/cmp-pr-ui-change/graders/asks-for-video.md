---
type: regex
pattern: '^[^\n]*(?:not confirmed|not (?:yet )?(?:attached|included|added|available|recorded|provided|shown)|missing|pending|to be added|\btodo\b|\btbd\b|\b(?:add|attach|upload|record)\b|\bno\b)[^\n]*\b(?:videos?|recordings?|screencasts?|GIFs?|clips?)\b|^[^\n]*\b(?:videos?|recordings?|screencasts?|GIFs?|clips?)\b[^\n]*(?:not confirmed|not (?:yet )?(?:attached|included|added|available|recorded|provided|shown)|missing|pending|to be added|\btodo\b|\btbd\b|\b(?:add|attach|upload|record)\b)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
