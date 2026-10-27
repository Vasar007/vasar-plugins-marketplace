---
type: llm
focus: last_message
arm: both
---

The text under test is about the tool snapsync. These are the facts that it can use:

- `-k count`: keep `count` snapshots on the remote, and delete the older ones. The range is 1 to 365. The default is 30.
- The deletion starts after the new snapshot is complete, oldest first.
- A failed transfer deletes nothing.

Compare the text with the facts. If a value, default, limit, exit status, or date does not match, the result is FAIL. If the text states a fact that is not in the list, the result is FAIL. A retry count and a timeout are two examples. Otherwise the result is PASS.
