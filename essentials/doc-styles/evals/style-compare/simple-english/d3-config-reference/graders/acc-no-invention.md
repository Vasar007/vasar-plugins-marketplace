---
type: llm
focus: { source: file, path: docs/snapsync.conf.md }
arm: both
---

The text under test is about the tool snapsync. These are the facts that it can use:

- The configuration file has one directive on each line. A `#` starts a comment.
- `keep count`: the default is 30. The `-k` flag overrides it.
- `port number`: the default is 22.
- `exclude pattern` and `include pattern`: the patterns are globs. Each directive can repeat. The last match decides.
- `bandwidth rate`: the rate is in KB/s. 0 means no limit, and it is the default.
- A `source path { ... }` block sets `keep` and `exclude` for one source.
- An unknown directive stops `snapsync` with exit status 1 and the message `line N: unknown directive`.

Compare the text with the facts. If a value, default, limit, exit status, or date does not match, the result is FAIL. If the text states a fact that is not in the list, the result is FAIL. A retry count and a timeout are two examples. A one-sentence definition of a term is not a new fact. An obvious inference from the listed facts is not a new fact either. Otherwise the result is PASS.
