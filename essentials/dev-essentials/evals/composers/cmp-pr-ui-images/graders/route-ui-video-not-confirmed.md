---
type: regex
pattern: '^## UI changes\b(?:(?!\n## )[\s\S])*?Not confirmed:(?:[^\n]*|(?:\*\*)?[ \t]*\r?\n(?:[ \t]*\r?\n)?(?:[ \t]*(?:[-*+]|\d+[.)])[^\n]*\n)*?[ \t]*(?:[-*+]|\d+[.)])[^\n]*)\b(?:videos?|recordings?|screencasts?|GIFs?)\b'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-14-order-count-badge.md }
---
