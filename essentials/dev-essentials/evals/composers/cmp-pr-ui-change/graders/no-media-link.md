---
type: regex
pattern: '!\[[^\]\n]*\]\(|<(?:img|video)\b|user-attachments/|https?://[^\s)>\]]+\.(?:png|jpe?g|gif|webp|svg|mp4|webm|mov)\b'
flags: i
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
