---
description: If the user asks for reviewers with different points of view on a design, the audit-team command starts.
tags: [triggers, audit-team]
allowed_tools: [Skill, Read, Glob, Grep]
---

Before we build this, get a team of reviewers with different points of view to look at the design below.

Design: the export service writes each order to a CSV file. A nightly job uploads the files to object storage. If an upload fails, the file stays on disk, and the next run tries it again.
