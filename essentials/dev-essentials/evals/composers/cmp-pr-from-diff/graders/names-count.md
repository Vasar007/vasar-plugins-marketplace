---
type: regex
pattern: 'orders_count|orders? count|count(?:s|ing)? (?:the |their )?orders|(?:count|number) of [^.\n]{0,25}orders'
flags: i
target: { source: file, path: Notes/PRs/PR-user-tasks-12-customer-index.md }
---
