---
type: llm
focus: { source: file, path: pr.md }
arm: both
---

The text under test is about the tool snapsync. These are the facts that it can use:

- `src/xfer.c`: when the remote returns `ENOSPC`, stop, delete nothing, and exit with status 3. Before the change, the exit status was 1, and it came after the deletion of the oldest snapshot.
- `tests/test_full.c`: a new test for a full disk.
- `docs/cli.md`: the exit status 3 is new.
- Reason: issue #212. A user lost a snapshot on a full disk.
- `-k` does not change.

Compare the text with the facts. If a value, default, limit, exit status, or date does not match, the result is FAIL. If the text states a fact that is not in the list, the result is FAIL. A retry count and a timeout are two examples. Otherwise the result is PASS.
