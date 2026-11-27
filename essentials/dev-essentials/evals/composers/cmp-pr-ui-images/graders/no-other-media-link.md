---
type: regex
pattern: '!\[[^\]\n]*\]\((?!<?https://github\.com/user-attachments/assets/(?:0b6f1c2e-5d4a-4e8b-9f3a-2c7d8e9a1b01|7e2d9a4b-1c3f-4a6e-8b5d-9f0e1a2b3c04)\b)|<(?:img|video)\b(?![^>\n]*(?:0b6f1c2e-5d4a-4e8b-9f3a-2c7d8e9a1b01|7e2d9a4b-1c3f-4a6e-8b5d-9f0e1a2b3c04))|user-attachments/assets/(?!(?:0b6f1c2e-5d4a-4e8b-9f3a-2c7d8e9a1b01|7e2d9a4b-1c3f-4a6e-8b5d-9f0e1a2b3c04)\b)|https?://[^\s)>\]]+\.(?:png|jpe?g|gif|webp|svg|mp4|webm|mov)\b'
flags: i
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
