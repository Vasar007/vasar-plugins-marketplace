---
description: "The user asks for a task description and adds fix notes with a SQL statement, a function name, and a file path. The run must write the draft file with the title, the two fixed sections, and short change items. The draft holds no code, no function name, and no file path."
tags: [composers, route]
allowed_tools: [Skill, Agent, Read, Glob, Grep, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Write a task description for this change. The feature name is customer-index. The orders page of a big customer takes 2 seconds to load, because the orders table has no index on the customer column. We also want the store to give the order count of each customer. My notes for the fix: run `CREATE INDEX idx_orders_customer ON orders (customer)` in `connect()` of src/store.py, and add a function `orders_count(db, customer)`.
