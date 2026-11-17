---
type: llm
focus: last_message
---

The text under test is a review report of the design file `docs/design/refund-export.md`. Two sections of the design disagree. The section "Retention" says that the export host keeps each refund file for 30 days. The section "Cleanup" says that a nightly job deletes each refund file that is older than 7 days.

If the report says that the 30 days of the retention and the 7 days of the cleanup disagree, the result is PASS. The finding can be in any bucket of the report. Otherwise the result is FAIL.
