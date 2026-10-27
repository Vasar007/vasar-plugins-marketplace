---
type: llm
focus: { source: file, path: docs/snapsync.conf.md }
arm: both
---

For each question, find the answer in the text under test. The facts below are the key.

1. What is the default of `port`?
2. What does the tool do with an unknown directive?
3. In which unit is the `bandwidth` rate, and what does 0 mean?

Facts:

- The configuration file has one directive on each line. A `#` starts a comment.
- `keep count`: the default is 30. The `-k` flag overrides it.
- `port number`: the default is 22.
- `exclude pattern` and `include pattern`: the patterns are globs. Each directive can repeat. The last match decides.
- `bandwidth rate`: the rate is in KB/s. 0 means no limit, and it is the default.
- A `source path { ... }` block sets `keep` and `exclude` for one source.
- An unknown directive stops `snapsync` with exit status 1 and the message `line N: unknown directive`.

If an answer is wrong or missing, the result is FAIL. If an answer is only in a part that does not name its subject, the result is FAIL. Otherwise the result is PASS.
