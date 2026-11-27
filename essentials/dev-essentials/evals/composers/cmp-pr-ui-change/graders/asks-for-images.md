---
type: regex
pattern: '^[^\n]*(?:not confirmed|not (?:yet )?(?:attached|included|added|available|captured|provided|shown|taken)|missing|pending|to be added|\btodo\b|\btbd\b|\b(?:add|attach|upload|capture|take)\b|\bno\b)[^\n]*\b(?:screenshots?|images?|pictures?|screen ?captures?)\b|^[^\n]*\b(?:screenshots?|images?|pictures?|screen ?captures?)\b[^\n]*(?:not confirmed|not (?:yet )?(?:attached|included|added|available|captured|provided|shown|taken)|missing|pending|to be added|\btodo\b|\btbd\b|\b(?:add|attach|upload|capture|take)\b)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
