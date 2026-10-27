---
type: llm
focus: last_message
arm: both
---

The text under test is about the tool snapsync. These are the facts that it can use:

- If the remote disk is full, the exit status is 3, and `snapsync` deletes no snapshot.
- The deletion of old snapshots starts after the new snapshot is complete, oldest first.
- The fix is to free space on the remote, or to lower `-k`. Then run `snapsync` again.

Compare the text with the facts. If a value, default, limit, exit status, or date does not match, the result is FAIL. If the text states a fact that is not in the list, the result is FAIL. A retry count and a timeout are two examples. Otherwise the result is PASS.
