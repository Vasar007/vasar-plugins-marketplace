---
type: llm
focus: last_message
---

The text under test answers the question whether pull request 42 of `example-org/pager` passes the merge gate. The gate passes: both of its check runs passed, and its merge state is `clean`. So the pull request is ready for a merge.

Find what the text says about the result of the gate, or about the readiness of the pull request for a merge. The answer can be a sentence, a label line such as "Gate: passed", or a row of a table.

If the text says that the gate passes, or that the pull request is ready for a merge, the result is PASS. A text that says that each item of the gate holds says the same. So does a text that says that the pull request can be merged now, or that nothing blocks the merge.

If the text says that the gate fails, the result is FAIL. If the text says that the pull request is not ready, is not yet ready, or is blocked, the result is FAIL. If the text gives two answers on the gate that disagree, the result is FAIL. If the text gives no answer on the gate, the result is FAIL.

Do not judge whether the pull request was merged. A sentence such as "I did not merge it" or a label such as "Merged: no" says nothing about the gate. A text that says that the merge waits for the approval of the user does not say that the pull request is blocked.

The text can also name a problem in the code of the pull request. That alone is not a FAIL, because the gate does not review the code.
