---
description: "The user asks for a GitHub issue with two labels, and the repository has only one of them. The run must create the issue with the label that exists and with the two fixed sections. Then it must read the issue back and report the URL of the read-back. It must name the label that it did not keep."
tags: [composers, mocks, route]
plugins: ["../../..", "../../../eval-stubs/github"]
allowed_tools: [Skill, Agent, Read, Glob, Grep, TodoWrite]
max_turns: 40
timeout_seconds: 900
---

Create a GitHub issue in example-org/pager. Title: Add an index on customer to the orders table. The orders page of a big customer takes 2 seconds to load, because the orders table has no index on the customer column. Add the labels feature and performance.
