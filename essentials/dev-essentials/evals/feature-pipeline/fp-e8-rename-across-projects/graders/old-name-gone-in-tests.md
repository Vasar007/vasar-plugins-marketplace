---
type: regex
pattern: '\.GetQuantity\('
match: not_contains
target: { source: file, path: tests/Inventory.Tests/StockServiceTests.cs }
---
