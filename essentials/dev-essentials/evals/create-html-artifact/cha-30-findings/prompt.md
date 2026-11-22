---
description: A report of 30 review findings as an HTML file. The file must hold every finding, and no finding that was not in the list. It must use no external stylesheet. The final message must end with an ARTIFACT line.
tags: [create-html-artifact, route, smoke]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 40
timeout_seconds: 900
---

Render these 30 review findings as an HTML report. Save it as review-findings.html.

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
- F-13 High src/billing/invoice.py:94 The invoice number repeats after a restart of the service.
- F-14 High src/billing/tax.py:11 The tax is rounded for each line and not for the whole order.
- F-15 Medium src/users/auth.py:18 The login page does not limit the number of tries.
- F-16 Low src/users/profile.py:25 The profile update accepts an empty name.
- F-17 Critical src/api/routes.py:32 The route for the order list ignores the page size.
- F-18 Medium src/api/errors.py:39 The error handler hides the real status code.
- F-19 Low src/store/cache.py:46 The cache never expires an entry.
- F-20 High src/store/queries.py:53 The query for one customer reads the whole table.
- F-21 Medium src/orders/export.py:60 The export uses the local time zone and not UTC.
- F-22 Low src/orders/import.py:67 The import stops at the first bad row and loses the rest.
- F-23 High src/billing/invoice.py:74 The invoice shows the old price after a price change.
- F-24 Medium src/billing/tax.py:81 The tax table has two rows for the same region.
- F-25 Low src/users/auth.py:88 The password reset link works more than once.
- F-26 High src/users/profile.py:95 The profile photo has no size limit.
- F-27 High src/api/routes.py:12 The route for a deleted order gives an empty page.
- F-28 Medium src/api/errors.py:19 The error log holds the card number of the user.
- F-29 Low src/store/cache.py:26 The cache holds the data of one user for another user.
- F-30 Critical src/store/queries.py:33 The query for the report has no index.
