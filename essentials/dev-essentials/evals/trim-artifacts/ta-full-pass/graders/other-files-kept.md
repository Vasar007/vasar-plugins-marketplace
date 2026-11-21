---
type: regex
pattern: '^(?=[\s\S]*^notes/README\.md$)(?=[\s\S]*^notes/decisions\.md$)(?=[\s\S]*^notes/requirements\.md$)(?=[\s\S]*^notes/open-questions\.md$)(?=[\s\S]*^notes/risks\.md$)(?=[\s\S]*^notes/plan\.md$)(?=[\s\S]*^notes/tools\.md$)(?=[\s\S]*^notes/interfaces\.md$)(?=[\s\S]*^notes/research-cache\.md$)(?=[\s\S]*^notes/handoff\.md$)(?=[\s\S]*^notes/glossary\.md$)'
flags: m
target: { source: file, path: trim-listing.txt }
---
