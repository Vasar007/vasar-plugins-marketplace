---
description: A report of 12 review findings as an HTML file. The file must hold every finding, and no finding that was not in the list. It must use no external stylesheet. The final message must end with an ARTIFACT line.
tags: [create-html-artifact, route, smoke]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 40
timeout_seconds: 900
---

Render these 12 review findings as an HTML report. Save it as review-findings.html.

- F-01 High src/orders/export.py:10 The CSV export drops the last row.
- F-02 Medium src/orders/import.py:17 The import accepts a file with no header row.
- F-03 Low src/billing/invoice.py:24 The invoice total cuts off the cents.
- F-04 Critical src/billing/tax.py:31 The tax rate of a missing region is zero.
- F-05 Medium src/users/auth.py:38 A user with an expired token can still read an order.
- F-06 Low src/users/profile.py:45 The profile page shows the email of another user after a fast switch.
- F-07 High src/api/routes.py:52 The route for old order links gives a 500 error.
- F-08 Medium src/api/errors.py:59 The error text shows the path of the server.
- F-09 Low src/store/cache.py:66 The cache key leaves out the language.
- F-10 High src/store/queries.py:73 The query for recent orders has no limit.
- F-11 Medium src/orders/export.py:80 The export file name has no date, so a new export replaces the old one.
- F-12 Low src/orders/import.py:87 The import keeps a row with a negative quantity.
