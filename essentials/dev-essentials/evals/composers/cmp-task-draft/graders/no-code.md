---
type: regex
pattern: 'CREATE INDEX|idx_orders_customer|connect\(|orders_count|src/|\.py\b|```'
match: not_contains
target: { source: file, path: notes/Tasks/task-customer-index.md }
---
