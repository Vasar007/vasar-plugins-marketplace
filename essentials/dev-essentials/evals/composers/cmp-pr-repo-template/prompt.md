---
description: "The repository has a PR template with its own headings. Its rules are only in HTML comments, and the prompt does not name it. The prompt gives the diff of a branch with a new function, a new test file, and no test run. The session has no shell tool. The run must save a PR description with the headings of the template in their order and no What section. The text holds no comment of the template. Its Evidence section says that the tests did not run, and it claims no pass. A last line names the agent tool and the model. The check box of the template for a passed test run stays empty."
tags: [composers, route]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 30
timeout_seconds: 600
---

Compose a PR description for my branch `user/tasks/12-customer-index`. The base branch is `main`. This session has no shell, so do not run git. Use the diff below as the git diff of the branch. The invoice header needs the order count of a customer. Save the draft in the notes folder `notes/`.

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
