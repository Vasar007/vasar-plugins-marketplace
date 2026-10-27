---
description: The model writes the test report of a snapsync release candidate.
name: obsd-a3-report
tags: [style-compare, style-compare-openbsd]
plugins: ["../../../.."]
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 20
timeout_seconds: 600
append_system_prompt: 'Writing rule: before you write English text, load the doc-styles:openbsd-style-docs skill with the Skill tool, and follow it. The rule covers files and your reply, not only documentation.'
---

Write `report.md`, the test report of the release candidate.

Facts:

- Release candidate 2.4. 212 tests ran, and 209 passed.
- Failures: `test_sparse_files` (a timeout after 120 seconds, only on FreeBSD 14), `test_ipv6_port` and `test_ipv6_list` (connection refused, because the CI runner has no IPv6).
- A 10 GiB source took 4 min 12 s. Release 2.3 took 4 min 30 s.
- No test covers files over 2 GiB.

Use only these facts.
