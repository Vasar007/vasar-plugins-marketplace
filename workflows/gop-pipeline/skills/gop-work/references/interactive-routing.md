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
  - **Dismiss specific findings and proceed** → for a dismissal of all CRITICALs, treat it as an override. Proceed to Phase 5 with a warning note in the commit message.
  - **Request manual fix** → the user wants to fix it outside the pipeline. Stop, and wait until the user says that the run can resume.
