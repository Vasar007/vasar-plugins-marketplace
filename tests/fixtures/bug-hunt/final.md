# Bug hunt report: sample-project

## Scope

- Project: sample-project. GitHub repository: owner/sample-project.
- Analyzed code: main at commit 1111111.
- Base branch for "Also on base": release at commit 2222222, from the local branch.

## Summary

Findings: 3. Confirmed: 1. Unconfirmed (needs owner review): 1. Rejected: 1. Duplicate: 0.

| ID | Title | Area | Severity | Confidence | Verdict | Also on base |
| --- | --- | --- | --- | --- | --- | --- |
| BH-01 | Export drops the last order | Area 1 | High | High | Confirmed | Yes |
| BH-02 | Invoice total ignores a credit \| refund | Area 2 | Medium | Low | Unconfirmed (needs owner review) | No |
| BH-03 | Retry loop never ends | Area 2 | Low | Medium | Rejected | No |

### For the owner's review

- BH-02: decide whether a credit note counts as a refund.

## Known issues that this report does not repeat

- #12: Slow export. Source: open issue with the label "bug".

## Area 1: Orders

Files: `src/orders/`. Out of scope: none.

### New details for known issues

None.

### BH-01: Export drops the last order

- Severity: High
- Confidence: High
- Category: Wrong result
- Location: `src/orders/export.ext:142`
- Also on base: Yes, `src/orders/export.ext:139`
- Verdict: Confirmed

Problem: The loop stops one item early.

Failure scenario: With three orders, the export file holds two.

Evidence: `src/orders/export.ext:142` uses `<` with `count - 1`.

Fix idea: Loop to `count`.

Verification: I ran the export on three orders and got two rows.

### Notes for other areas

- For Area 2 (Invoices): `src/invoices/total.ext:10`: the same loop form. Result: BH-02.

## Area 2: Invoices

Files: `src/invoices/`. Out of scope: none.

### New details for known issues

None.

### BH-02: Invoice total ignores a credit | refund

- Severity: Medium
- Confidence: Low
- Category: Wrong result
- Location: `src/invoices/total.ext:10`
- Also on base: No (new in the analyzed commit)
- Verdict: Unconfirmed (needs owner review)

Problem: The total does not subtract a credit note.

Failure scenario: Not shown: no test data with a credit note.

Evidence: Not confirmed: the credit path. I looked at `total.ext`.

Fix idea: Subtract credit notes.

Verification: I read the code but found no test data.

Not covered: the credit note import.

Where I looked: `src/invoices/total.ext`.

To decide: whether a credit note counts as a refund.

### Notes for other areas

None.

## Appendix: rejected findings

### BH-03: Retry loop never ends

- Severity: Low
- Confidence: Medium
- Category: Other: retry
- Location: `src/invoices/retry.ext:5`
- Also on base: No (new in the analyzed commit)
- Verdict: Rejected

Problem: The retry loop has no limit.

Failure scenario: A server that always fails.

Evidence: `retry.ext:5` loops on failure.

Fix idea: Add a limit.

Verification: The caller sets a limit of three tries at `retry.ext:2`.
