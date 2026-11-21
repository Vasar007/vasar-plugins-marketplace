---
type: regex
pattern: 'namespace\s+Inventory\.Tests\x3b\s+\[TestFixture\]\s+public\s+sealed\s+class\s+StockServiceTests\s+\{[\s\S]*?\}\s+\[Test\]\s+public\s+void\s+Restock_ThenGetQuantity_ReturnsNewAmount\(\)\s+\{\s+var\s+service\s+=\s+new\s+StockService\(new\s+FakeSqlRunner\(\)\)\x3b\s+var\s+before\s+=\s+service\.GetQuantity\("ab-1"\)\x3b\s+service\.Restock\("ab-1",\s+5\)\x3b\s+var\s+after\s+=\s+service\.GetQuantity\("ab-1"\)\x3b\s+Assert\.That\(before,\s+Is\.EqualTo\(0\)\)\x3b\s+Assert\.That\(after,\s+Is\.EqualTo\(5\)\)\x3b\s+\}'
target: { source: file, path: tests/Inventory.Tests/StockServiceTests.cs }
---
