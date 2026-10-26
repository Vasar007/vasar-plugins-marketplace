---
expect:
  owner: example-org
  repo: shop
---

{
  "number": 17,
  "title": "Stock level of one warehouse shows the level of another warehouse",
  "state": "open",
  "labels": [
    {
      "name": "bug"
    }
  ],
  "user": {
    "login": "example-reporter"
  },
  "body": "Two warehouses that hold the same sku show the same stock level. The cache in inventory/cache.py looks like the cause."
}
