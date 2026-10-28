---
type: llm
focus: { source: file, path: report.md }
arm: both
---

For each question, find the answer in the text under test. The facts below are the key.

1. How many tests ran, and how many passed?
2. Why did the IPv6 tests fail?
3. Which gap in the tests does the report name?

Facts:

- Release candidate 2.4. 212 tests ran, and 209 passed.
- Failures: `test_sparse_files` (a timeout after 120 seconds, only on FreeBSD 14), `test_ipv6_port` and `test_ipv6_list` (connection refused, because the CI runner has no IPv6).
- A 10 GiB source took 4 min 12 s. Release 2.3 took 4 min 30 s.
- No test covers files over 2 GiB.

If an answer is wrong or missing, the result is FAIL. If an answer is only in a part that does not name its subject, the result is FAIL. Otherwise the result is PASS.
