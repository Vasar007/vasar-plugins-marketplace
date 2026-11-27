---
description: "The prompt of cmp-pr-untested-diff, plus a short run report. The report has a review finding that stays open with its follow-up issue, and a choice of the plan with its reason. The session has no shell tool. The run must save a PR description that names the open finding with its issue and the choice with its reason. It adds no closing keyword for the follow-up issue. The route grader reads both points in the Notes section."
tags: [composers, route]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 30
timeout_seconds: 600
---

Compose a PR description for my branch `user/tasks/12-customer-index`. The base branch is `main`. This session has no shell and no git repository, so do not run git. Use the diff below as the git diff of the branch. The invoice header needs the order count of a customer. Save the draft in the notes folder `notes/`.

Here is the report of the run on this branch:

- Review: one Medium finding stays open. `orders_count` also counts cancelled orders. The follow-up is issue #77.
- Decision: `orders_count` counts the rows on each call and keeps no counter column, on purpose. A counter column can drift from the orders table.

```diff
diff --git a/src/store.py b/src/store.py
index 3b18e51..9c2f4d7 100644
--- a/src/store.py
+++ b/src/store.py
@@ -20,3 +20,8 @@ def orders_for_customer(db, customer, limit=50):
         (customer, limit),
     )
     return rows.fetchall()
+
+
+def orders_count(db, customer):
+    """Return the number of orders of a customer."""
+    return db.execute("SELECT COUNT(*) FROM orders WHERE customer = ?", (customer,)).fetchone()[0]
diff --git a/tests/test_orders_count.py b/tests/test_orders_count.py
new file mode 100644
index 0000000..5e1c2a8
--- /dev/null
+++ b/tests/test_orders_count.py
@@ -0,0 +1,12 @@
+import unittest
+
+from src import store
+
+
+class OrdersCountTests(unittest.TestCase):
+    def test_orders_count(self):
+        db = store.connect()
+        store.add_order(db, "ada", 10)
+        store.add_order(db, "ada", 30)
+        self.assertEqual(store.orders_count(db, "ada"), 2)
+        self.assertEqual(store.orders_count(db, "bob"), 0)
```
