---
type: llm
focus: { source: file, path: report.md }
arm: both
---

The text under test is about the tool snapsync. These are the facts that it can use:

- Release candidate 2.4. 212 tests ran, and 209 passed.
- Failures: `test_sparse_files` (a timeout after 120 seconds, only on FreeBSD 14), `test_ipv6_port` and `test_ipv6_list` (connection refused, because the CI runner has no IPv6).
- A 10 GiB source took 4 min 12 s. Release 2.3 took 4 min 30 s.
- No test covers files over 2 GiB.

Compare the text with the facts. If a value, default, limit, exit status, or date does not match, the result is FAIL. If the text states a fact that is not in the list, the result is FAIL. A retry count and a timeout are two examples. Otherwise the result is PASS.
