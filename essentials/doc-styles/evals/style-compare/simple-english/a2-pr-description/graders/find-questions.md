---
type: llm
focus: { source: file, path: pr.md }
arm: both
---

For each question, find the answer in the text under test. The facts below are the key.

1. What exit status does a full remote disk give now, and what was it before?
2. Why does the change exist?
3. What does the change leave as it is?

Facts:

- `src/xfer.c`: when the remote returns `ENOSPC`, stop, delete nothing, and exit with status 3. Before the change, the exit status was 1, and it came after the deletion of the oldest snapshot.
- `tests/test_full.c`: a new test for a full disk.
- `docs/cli.md`: the exit status 3 is new.
- Reason: issue #212. A user lost a snapshot on a full disk.
- `-k` does not change.

If an answer is wrong or missing, the result is FAIL. If an answer is only in a part that does not name its subject, the result is FAIL. Otherwise the result is PASS.
