---
type: regex
pattern: 'orders_count|orders?[ -]count|(?<!\brow )(?<!\brows )\bcount(?:s|ing)?\b[^.\n]{0,25}\borders|number of (?:the |their |a customer.s )?orders|how many orders|orders?[ -]per[ -]customer'
flags: i
target: { source: file, path: Notes/PRs/PR-user-tasks-12-customer-index.md }
---
