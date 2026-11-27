---
description: "The user gives the diff of a branch in the prompt. The diff changes a view: a new badge in a page header, with its style and a fade-in animation. The prompt holds no image and no video. The session has no shell tool. The run must save a short PR description in the default form. It asks for the images of the view before and after the change, and for a short video of the animation. It marks them as not there yet. It holds no image link and claims no evidence that the input lacks. The route graders read the new section UI changes."
tags: [composers, route]
allowed_tools: [Skill, Read, Glob, Grep, TodoWrite]
max_turns: 30
timeout_seconds: 600
---

Compose a PR description for my branch `user/tasks/14-order-count-badge`. The base branch is `main`. This session has no shell and no git repository, so do not run git. Use the diff below as the git diff of the branch. Support staff asked for the order count of a customer in the invoice header. Save the draft in the notes folder `notes/`.

```diff
diff --git a/web/templates/invoice_header.html b/web/templates/invoice_header.html
index 4c1d2e0..8a7f3b1 100644
--- a/web/templates/invoice_header.html
+++ b/web/templates/invoice_header.html
@@ -1,5 +1,8 @@
 <header class="invoice-header">
   <h1>Invoice {{ invoice.number }}</h1>
   <p class="customer">{{ customer.name }}</p>
+  <span class="order-count" title="Orders of this customer">
+    {{ customer.orders_count }} orders
+  </span>
   <p class="date">{{ invoice.date }}</p>
 </header>
diff --git a/web/static/invoice.css b/web/static/invoice.css
index 1b2c3d4..5e6f7a8 100644
--- a/web/static/invoice.css
+++ b/web/static/invoice.css
@@ -12,3 +12,17 @@
 .invoice-header .customer {
   font-weight: 600;
 }
+
+.invoice-header .order-count {
+  display: inline-block;
+  padding: 2px 8px;
+  border-radius: 12px;
+  background: #e8f0fe;
+  color: #1a4fb4;
+  animation: count-fade-in 300ms ease-out;
+}
+
+@keyframes count-fade-in {
+  from { opacity: 0; }
+  to { opacity: 1; }
+}
```
