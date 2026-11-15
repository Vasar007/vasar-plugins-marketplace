---
expect:
  query: string
---

{"total_count": 2, "incomplete_results": false, "items": [{"number": 57, "title": "Add an index on the created_at column of orders", "state": "open", "html_url": "https://github.com/example-org/pager/issues/57", "body": "The order history query sorts by created_at, and the column has no index.\n\nSource: https://github.com/example-org/pager/pull/31#discussion_r8820"}, {"number": 58, "title": "Add an index on the customer column of orders", "state": "open", "html_url": "https://github.com/example-org/pager/issues/58", "body": "The orders table has no index on customer, so each lookup by customer reads the whole table.\n\nSource: https://github.com/example-org/pager/pull/42#discussion_r9103"}]}
