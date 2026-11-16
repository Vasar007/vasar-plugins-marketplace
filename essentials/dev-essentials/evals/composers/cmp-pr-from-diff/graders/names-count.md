---
type: regex
pattern: 'orders_count|orders?[ -]count|\bcount(?:s|ing)?\b[^.\n]{0,25}\borders|number of (?:the |their |a customer.s )?orders'
flags: i
target: { source: file, path: Notes/PRs/PR-user-tasks-12-customer-index.md }
---
