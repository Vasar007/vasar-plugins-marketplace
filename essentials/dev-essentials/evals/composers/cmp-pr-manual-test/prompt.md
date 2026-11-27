---
description: "The prompt of cmp-pr-untested-diff, plus a manual test of the user with what the user saw, and a database that nobody tested. The session has no shell tool. The run must save a PR description whose Testing section names the manual test and its result. It names the untested database as not tested. The route grader reads the untested database after Not confirmed: in the Testing section."
tags: [composers, route]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 30
timeout_seconds: 600
---

Compose a PR description for my branch `user/tasks/12-customer-index`. The base branch is `main`. This session has no shell and no git repository, so do not run git. Use the diff below as the git diff of the branch. The invoice header needs the order count of a customer. Save the draft in the notes folder `notes/`.

I tested it by hand on a copy of the production database. For a customer with two orders, `orders_count` returned 2. For a customer with no orders, it returned 0. The copy is a SQLite file, so nobody ran it on the Postgres server of production.

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
