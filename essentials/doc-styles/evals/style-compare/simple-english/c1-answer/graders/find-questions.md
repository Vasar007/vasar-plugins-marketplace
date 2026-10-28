---
type: llm
focus: last_message
arm: both
---

For each question, find the answer in the text under test. The facts below are the key.

1. Why did the exit status 3 happen?
2. Why is the oldest snapshot still there?
3. What does the user do?

Facts:

- If the remote disk is full, the exit status is 3, and `snapsync` deletes no snapshot.
- The deletion of old snapshots starts after the new snapshot is complete, oldest first.
- The fix is to free space on the remote, or to lower `-k`. Then run `snapsync` again.

If an answer is wrong or missing, the result is FAIL. If an answer is only in a part that does not name its subject, the result is FAIL. Otherwise the result is PASS.
