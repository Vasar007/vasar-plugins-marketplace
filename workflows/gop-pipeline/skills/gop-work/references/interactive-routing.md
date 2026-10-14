# Interactive routing of validation results

`gop-work` reads this file at step 19, in a run with `--interactive`. The aggregated report of step 18 is the input.

**IF `validation_status` is APPROVED:**
- Proceed directly to Phase 5. No user interaction needed.

**IF `validation_status` is APPROVED_WITH_WARNINGS:**
- Present the aggregated report to the user. Show all warnings with their confidence percentages, domain, proposals, and `also_seen_by` annotations.
- Format as a numbered list the user can act on:
  ```
  Validators found warnings with improvement proposals. Review and decide:

  1. [CORR-01] <title> (Confidence: nn%)
     File: path/to/file.cs
     Proposal: <description>

  2. [SEC-02] <title> (Confidence: nn%) [also seen by: REUSE-03]
     File: ...
     Proposal: ...

  Options:
  a) Accept all proposals → re-run implementation with these fixes
  b) Accept specific proposals (e.g., "1, 3") → re-run with selected fixes only
  c) Reject all → proceed to commit as-is
  ```
- If the user accepts any proposals: collect accepted proposals into `validator_proposals`, return to Phase 1 with this context, then re-run Phases 2–4.
- If the user rejects all proposals: proceed to Phase 5.

**IF `validation_status` is BLOCKED:**
- Present the aggregated report to the user, grouping findings by confidence:
  - **High-confidence findings (≥ 90%):** present them with a strong recommendation to fix. These are very likely real issues.
  - **Lower-confidence findings (< 90%):** present them with an explicit note that the specialist is uncertain. These can be false positives.
- Include all proposals (both criticals and warnings) in the same numbered-list format as above, with domain prefix and `also_seen_by` annotations preserved.
- User options:
  - **Accept proposals** → collect accepted proposals into `validator_proposals`, return to Phase 1, re-run Phases 2–4
  - **Dismiss specific findings and proceed** → record the IDs and titles of the dismissed findings for the rest of this run.
    - If no CRITICAL finding remains, override and proceed to Phase 5. Pass the dismissed CRITICAL findings to `gop-commit` as `warning_note` (step 20 of `SKILL.md`).
    - If CRITICAL findings remain, show only the remaining findings, with the same options, and route again.
  - **Request manual fix** → the user wants to fix it outside the pipeline. Stop, and wait until the user says that the run can resume.
- The user can combine options in one answer. Example: dismiss one CRITICAL finding and accept the proposal for another one. Then return to Phase 1 with the accepted proposals.
- In each later validation cycle of this run, a finding with the same file and the same issue as a dismissed finding counts as dismissed. Do not ask about it again. It does not make the status `BLOCKED`. If it is CRITICAL, keep it in the `warning_note` list.
