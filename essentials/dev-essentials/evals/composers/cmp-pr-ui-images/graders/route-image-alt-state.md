---
type: regex
pattern: '^(?=[\s\S]*!\[(?=[^\]\n]*\b(?:badge|counts?|orders?|missing|without|shows?|no|with)\b)[^\]\n]*\]\(<?https://github\.com/user-attachments/assets/0b6f1c2e-5d4a-4e8b-9f3a-2c7d8e9a1b01\b)(?=[\s\S]*!\[(?=[^\]\n]*\b(?:badge|counts?|orders?|missing|without|shows?|no|with)\b)[^\]\n]*\]\(<?https://github\.com/user-attachments/assets/7e2d9a4b-1c3f-4a6e-8b5d-9f0e1a2b3c04\b)'
flags: i
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
