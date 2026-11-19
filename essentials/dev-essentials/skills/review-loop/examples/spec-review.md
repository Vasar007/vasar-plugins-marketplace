# Example — Spec / Design Document Review

A worked example of the review of a spec change document (`target=spec`). The document can come from any spec framework. A spec change can be a folder, for example an OpenSpec change at `openspec/changes/<name>/`, or a single file in another framework. This example uses an OpenSpec change at `openspec/changes/add-tenant-quotas/`. Its paths, its validator command, and its precedent spec are those of OpenSpec. With another framework, use the change path and the validator of that framework. The flow stays the same.

## Contents

- Invocation
- Phase 1: Resolve target
- Phase 2: Resolve reviewer + fixer
- Phase 3: Round 1 review
- Phase 4: Triage
- Phase 5: Verify-then-fix
- Phase 6: Build / test verify
- Phase 7: Commit
- Phase 8: Stop
- Phase 9: Final summary (printed to chat: single cycle, no `--save-reports`)
- Full format: Round 1 report
- Description
- Summary table
- Details per item
- Conclusion
- Final verdict
- Reviewer model

The example shows how a spec review differs from a code review. There is no build step, and the fixes are edits of the spec. The validation runs the validator of the spec framework of the repository (here, `openspec validate`) instead of a compiler. OpenSpec keeps an active change in `openspec/changes/<name>/` and moves a completed change to `openspec/changes/archive/<YYYY-MM-DD>-<name>/`.

---

## Invocation

```text
/review-loop target=spec openspec/changes/add-tenant-quotas/proposal.md --rounds=1 --reviewer=audit-team --skip=medium,low,nit --mode interactive
```

Resolved parameters: `target=spec <path>`, `--rounds=1`, `--reviewer=audit-team`, `--fixer=general-purpose` (the default), and `--skip=medium,low,nit` (explicit, because the default is `none`). The mode is interactive, so that this example shows the stop at the triage.

---

## Phase 1 — Resolve target

`target=spec`: read the file in full, and brief the reviewer for a spec review.

```text
Resolved: openspec/changes/add-tenant-quotas/proposal.md (spec target)
Reading full file... 412 lines loaded.
```

---

## Phase 2 — Resolve reviewer + fixer

`--reviewer audit-team`: the target is `spec <path>`, a documentation path, so the adapter applies with no fallback. Argument mapping: `<path>` is the resolved path of `proposal.md`. `--audit-team-args` is not set, so `[agent-count]` gets the fixed value `5` of the adapter, which keeps the five-role team. `--reviewer-model` is `opus`, the default of this skill for the flag. So the skill passes it as the `[model]` argument of `/audit-team`, and the dispatch is `/audit-team openspec/changes/add-tenant-quotas/proposal.md 5 opus`. `--fixer general-purpose` (the default) resolves with no fallback.

---

## Phase 3 — Round 1 review

`/audit-team` uses its own role prompts (see the adapter). The `spec` brief of `references/reviewer-briefs.md` is not passed.

`audit-team` returns four findings. The adapter of Phase 2 maps them from the buckets Blockers, Warnings, and Suggestions:

- Items 1 and 2 were `Blockers`. Item 2 is graded down to Critical, because the contradiction behind it is a logic defect, not a gap that blocks the implementation.
- Items 3 and 4 were `Warnings`. Item 4 is graded down to Medium, because it flags a `should` that is not normative, not a defect.

| # | Severity | Type | Location | What's wrong |
|---|---|---|---|---|
| 1 | Blocker | Spec | §4 "Rate-Limiting Algorithm" | The window size, the reset semantics, and the boundary behavior are undefined. A correct implementation is impossible. |
| 2 | Critical | Spec | §3 vs §7 | §3 tests the quota before dispatch. §7 decrements the counter only after a success. So failed requests bypass the quota, and enforcement breaks under high error rates. |
| 3 | High | Spec | §5 "Error Handling" | No HTTP status, body schema, log line, or event for a quota-exceeded case |
| 4 | Medium | Spec | §2 "Overview" | The text `should typically be enforced at the gateway layer` is not normative, so the enforcement layer is not specified. |

Review made by `opus`

---

## Phase 4 — Triage

```text
Round 1 findings:
  Blocker:  1  (will fix; 1 blocking)
  Critical: 1  (will fix; 1 blocking)
  High:     1  (will fix; 1 blocking)
  Medium:   1  (deferred — --skip medium; 0 blocking)
  Low:      0  (deferred — --skip low; 0 blocking)
  Nit:      0  (deferred — --skip nit; 0 blocking)

Proceeding to verify+fix 3 issues. Deferring 1.
```

Findings #1 to #3 are the Blocker, the Critical, and the High. Each one is `blocking: true` by default. #4 (Medium) is `blocking: false`, because the explicit `--skip medium` defers it, and nothing in its text raises it.

The skill waits for the acknowledgment. The user replies "proceed".

---

## Phase 5 — Verify-then-fix

Target file: `openspec/changes/add-tenant-quotas/proposal.md`. In a spec review, a fix is an edit of the spec, not a change of code.

**Step 5a**. `/audit-team` returns no fix plan. So one plan dispatch on `--reviewer-model` plans the fix of #1 to #3, as the adapter says. The three fixes edit one file, so the orchestrator is the fixer (step 5b, context test). It works from that plan.

**#1: APPLY**. Verification source: `openspec/changes/archive/2025-11-01-resource-limits/proposal.md` uses fixed windows of 60 seconds. The fixer rewrote §4. It now gives the window size (60 s, aligned to the wall clock) and the reset trigger (the crossing of a boundary). It also gives the rule for an arrival at a boundary: the request counts against the window that it arrives in.

```text
Edit: proposal.md §4 — 3 paragraphs rewritten with explicit window definition.
```

**#2: APPLY**. Verification source: the contradiction is plain from §3 and §7. The correct semantics (consume at admission, and failures count) match the existing `resource-limits` spec ("admit-then-count, no reclaim on failure"). The fixer deleted the decrement sentence of §7. It added a sentence that ties the decrement to the admission of §3. The sentence says that failed requests consume quota and get no refund.

```text
Edit: proposal.md §7 — deleted conflicting sentence; added clarification.
```

**#3: APPLY**. Verification source: `CLAUDE.md` §"HTTP Error Path Convention". Every error path must give the status, the body, the log level, and the event. The fixer added the subsection "Quota exceeded" to §5: HTTP 429, `{ "error": "quota_exceeded", "retryAfterSeconds": <N> }`, a WARN log, and no event.

```text
Edit: proposal.md §5 — added "Quota exceeded" subsection.
```

---

## Phase 6 — Build / test verify

`target=spec`: the target is not code. No `*.sln` or other build manifest applies.

```text
Spec target detected — build/test step skipped (non-code artifact).
```

The spec validation still applies, because `CLAUDE.md` documents a validator for the spec framework (here, `openspec validate <change-name>`):

```text
openspec validate add-tenant-quotas
✓ Schema valid
✓ All required sections present
✓ No broken internal references
```

The validation passed.

---

## Phase 7 — Commit

```bash
git add openspec/changes/add-tenant-quotas/proposal.md
git commit -m "Review round 1: Fix rate-limit algorithm, §3/§7 contradiction, missing quota-exceeded error path"
```

---

## Phase 8 — Stop

`--rounds=1`: the rounds used (1) equal the maximum (1). Stop verdict: **stop-max-rounds**.

> Note: `stop-max-rounds` is correct here, although the fixer handled all Blocker, Critical, and High findings. `stop-clean` needs a re-review pass that found no issues left in the fix diff (the rule of Phase 8). With a single round, no re-review runs, so the loop cannot prove a clean state. `stop-max-rounds` is the accurate verdict.

---

## Phase 9 — Final summary (printed to chat — single cycle, no `--save-reports`)

```markdown
## Review Loop Complete

Rounds: 1 of 1 max
Build: skipped (spec target — no compile command)
Tests: not run
Lint: not run (no lint command)
Spec validation: passing (openspec validate add-tenant-quotas)
Stop verdict: stop-max-rounds

### Round 1 (spec: openspec/changes/add-tenant-quotas/proposal.md)
  Found:    1 Blocker, 1 Critical, 1 High, 1 Medium, 0 Low, 0 Nit
  Fixed:    3 (APPLY=3, PARTIAL=0, REJECT=0)
  Deferred: 1 (per --skip medium / merit triage)

### Deferred items (by severity; (blocking) = Phase 4 marked it must-fix-before-merge)
  [Medium] #4: §2 "Overview" — "should typically" leaves enforcement layer undefined
```

---

## Full format — Round 1 report

# Review by AI Agent (Round-1) — spec: add-tenant-quotas/proposal.md

## Description

A spec change proposal (here, an OpenSpec change) that adds a quota for each tenant, enforced by a sliding-window rate limiter. 412 lines. It covers the algorithm, the error handling, and the API contract. This cycle fixed three spec-correctness issues.

## Summary table

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|---|---|---|---|---|
| 1 | Blocker | Spec | proposal.md:§4 | The window size, the reset semantics, and the boundary behavior are all undefined | Define the window size, the reset trigger, and the boundary rule explicitly |
| 2 | Critical | Spec | proposal.md:§3 + §7 | The test before dispatch (§3) contradicts the decrement after success (§7) | Delete the §7 sentence. Tie the decrement to the admission of §3 (failures count, no refund). |
| 3 | High | Spec | proposal.md:§5 | No observable response for a quota-exceeded case | Add HTTP 429, a body schema, a log level, and an event rule |
| 4 | Medium | Spec | proposal.md:§2 | `should typically` makes the enforcement layer not normative | Replace it with a MUST statement that names the required layer |

## Details per item

### 1 Undefined rate-limiting algorithm (§4)

- **Problem**: §4 says "within a sliding window", but gives no window size, reset semantics, or rule for an arrival at a boundary. Three implementers can build three incompatible counters.
- **Impact**: a correct implementation is impossible without a guess about the window semantics.
- **Confidence**: high. Section 4 gives no window size, and the quota precedent shows what the author most likely means.
- **Recommendation**: give the window size (60 s, fixed) and the reset trigger (the window boundary). Also give the boundary rule: a request counts against the window that it arrives in.
- **Verification source**: `openspec/changes/archive/2025-11-01-resource-limits/proposal.md`. The existing quota design uses fixed windows of 60 seconds. Align with that precedent.

### 2 §3 vs §7 contradiction on decrement timing

- **Problem**: §3 tests the quota before dispatch. §7 decrements only after a successful response. So a failed request costs nothing and does not drain the quota counter. Under a lasting failure rate, the real throughput can be far above the intended limit.
- **Impact**: workloads with many failures bypass the quota. Rate limiting does not work while error rates are high.
- **Confidence**: high. Sections 3 and 7 give two different decrement times for the same counter.
- **Recommendation**: delete the decrement sentence of §7. Add a note that the decrement happens at the admission of §3. The note also says that failed requests consume quota with no refund (admit-then-count, no reclaim on failure).
- **Verification source**: the `resource-limits` spec, with the same admit-then-count and no reclaim on failure.

### 3 Missing quota-exceeded error path (§5)

- **Problem**: §5 lists timeouts and auth failures, but says nothing about a quota-exceeded case: no HTTP status, no response body, no log entry, and no event.
- **Impact**: implementations differ, and client libraries and dashboards have nothing to match against.
- **Confidence**: high. Section 5 has no quota-exceeded case, and the repository convention requires one.
- **Recommendation**: add a subsection "Quota exceeded": HTTP 429, `{ "error": "quota_exceeded", "retryAfterSeconds": N }`, a WARN log with the entity ID and the limit, and no event.
- **Verification source**: `CLAUDE.md` §"HTTP Error Path Convention."

### 4 Non-normative enforcement-layer statement (§2)

- **Problem**: the text `should typically be enforced at the gateway layer` is not normative. Under this wording, enforcement in the service layer also complies.
- **Impact**: the services that implement this spec can use different architectures.
- **Confidence**: medium. The wording is not normative. The author can say that service-layer enforcement is acceptable.
- **Recommendation**: replace it with `MUST be implemented at the gateway layer`. If the service layer is also acceptable, say so explicitly.
- **Verification source**: no proof. This is a design preference. Flag it for the author to make the intent clear.

## Conclusion

- **Must fix before merge**: #1, #2
- **Acceptable risks**: none
- **Needs discussion**: #3 (Warning bucket, fixed this cycle as a High), #4 (the author makes the normative intent for the enforcement layer clear)

## Final verdict

✅➕ **Approve with suggestions**. The Blocker, the Critical, and the High are resolved. One Medium (#4) is deferred.

## Reviewer model

Review made by `opus`
