---
type: regex
pattern: '^## Testing\b(?:(?!\n## )[\s\S])*?(?:test_orders_count|orders_count|OrdersCount|order[ -]count|count of (?:the )?orders)'
flags: mi
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
