---
type: llm
focus: last_message
---

The text under test is a review report of the design file `docs/design/refund-export.md`. Step 4 of the design says: if the upload fails, wait until the network is stable, and then go to step 3. No test can check the condition "the network is stable", because the design does not define it.

If the report says that the wait condition of step 4 is vague, not defined, not measurable, or not testable, the result is PASS. If the report says that the wait of step 4 has no limit, no timeout, or no end, the result is also PASS. The finding can be in any bucket of the report. Otherwise the result is FAIL.
