---
type: regex
pattern: 'CREATE INDEX|idx_orders_customer|connect\(|orders_count|src/|```'
match: not_contains
target: { source: file, path: Notes/Tasks/task-customer-index.md }
---
