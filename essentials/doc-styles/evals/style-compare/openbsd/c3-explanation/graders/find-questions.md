---
type: llm
focus: last_message
arm: both
---

For each question, find the answer in the text under test. The facts below are the key.

1. What does `-k` do?
2. What starts the deletion, and which snapshots go first?
3. What does a failed transfer delete?

Facts:

- `-k count`: keep `count` snapshots on the remote, and delete the older ones. The range is 1 to 365. The default is 30.
- The deletion starts after the new snapshot is complete, oldest first.
- A failed transfer deletes nothing.

If an answer is wrong or missing, the result is FAIL. If an answer is only in a part that does not name its subject, the result is FAIL. Otherwise the result is PASS.
