---
type: regex
pattern: '(?:^|/)(?:CLAUDE|AGENTS|REVIEW)\.md$|(?:^|/)\.claude/(?:rules|skills|agents|commands)/'
flags: im
match: not_contains
target: files
---
