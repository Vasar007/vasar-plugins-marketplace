---
type: regex
pattern: '^[ \t]*(?:[-*+][ \t]+)?(?:#{1,6}[ \t]*|\*\*)(?:UI|User interface|Screenshots?|Visual changes|Before and after)\b|\bnot confirmed:[^\n]*\b(?:screenshots?|images?|videos?|recordings?)\b'
flags: mi
match: not_contains
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
