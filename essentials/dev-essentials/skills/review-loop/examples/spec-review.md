# Example — Spec / Design Document Review

Worked example: reviewing an OpenSpec change document (`target=spec`). Illustrates divergence
from a code review: no build step, fixes are spec edits, validation runs the repo's OpenSpec
validator instead of a compiler.

---

## Invocation

```text
/review-loop target=spec openspec/changes/2026-05-08-add-tenant-quotas/proposal.md --rounds=1 --reviewer=audit-team --skip=medium,low,nit
```

Parameters resolved: `target=spec <path>`, `--rounds=1`, `--reviewer=audit-team`,
`--fixer=general-purpose` (default), `--skip=medium,low,nit` (explicit — the default is `none`),
`--auto-proceed=off` (default).

---

## Phase 1 — Resolve target

`target=spec` → read the file in full; brief the reviewer for spec-style review.

```
Resolved: openspec/changes/2026-05-08-add-tenant-quotas/proposal.md (spec target)
Reading full file... 412 lines loaded.
```

---

## Phase 2 — Resolve reviewer + fixer

`--reviewer audit-team` → target is `spec <path>`, a documentation path, so the adapter is
eligible (no fallback). Argument mapping: `<path>` = the resolved `proposal.md` path;
`--audit-team-args` is unset, so `[agent-count]` fills with `/audit-team`'s own default (`5`);
`--reviewer-model` is `opus` (this skill's own default for the flag), so it is forwarded as
`/audit-team`'s `[model]` positional — the dispatch is `/audit-team proposal.md 5 opus`. `--fixer
general-purpose` (default) → resolves without fallback.

---

## Phase 3 — Round 1 review

Reviewer brief (from `references/reviewer-briefs.md` §`spec <path>`, paraphrased for this example):

> You are reviewing a **specification or design document**, not code. Read it as a skeptical
> implementer who must build exactly what is written — nothing more, nothing less. Your job is to
> find gaps, ambiguities, and contradictions before any implementation is written.
>
> **Focus areas (priority order):** Ambiguity → Undefined behavior → Missing error paths →
> Contradictions → Coverage gaps → Deferred decisions → Docs quality.
>
> **Not in scope:** code quality; checking whether an implementation matches this spec.

`audit-team` returns four findings (mapped from its Blockers/Warnings/Suggestions buckets per
Phase 2's adapter — items 1–2 were `Blockers`, with item 2 re-graded down to Critical because the
underlying contradiction is a logic defect rather than an implementation-blocking gap, items 3–4
`Warnings`, with item 4 re-graded down to Medium because it flags a non-normative "should" rather
than a defect):

| # | Severity | Type | Location | What's wrong |
|---|---|---|---|---|
| 1 | Blocker | Spec | §4 "Rate-Limiting Algorithm" | Window size, reset semantics, and boundary behavior undefined — correct implementation impossible |
| 2 | Critical | Spec | §3 vs §7 | §3: quota checked before dispatch; §7: counter decremented after success only — failed requests bypass quota, breaking enforcement under high error rates |
| 3 | High | Spec | §5 "Error Handling" | No HTTP status, body schema, log line, or event defined for quota-exceeded |
| 4 | Medium | Spec | §2 "Overview" | "should typically be enforced at the gateway layer" — non-normative; enforcement layer unspecified |

Review made by `claude-opus-4-7`

---

## Phase 4 — Triage

```
Round 1 findings:
  Blocker:  1  (will fix; 1 blocking)
  Critical: 1  (will fix; 1 blocking)
  High:     1  (will fix; 1 blocking)
  Medium:   1  (deferred — --skip medium; 0 blocking)
  Low:      0  (deferred — --skip low; 0 blocking)
  Nit:      0  (deferred — --skip nit; 0 blocking)

Proceeding to verify+fix 3 issues. Deferring 1.
```

Findings #1–#3 are the Blocker/Critical/High set — each `blocking: true` by default. #4 (Medium,
deferred via the explicit `--skip medium`) is `blocking: false`; nothing about its text elevates it.

Waiting for user acknowledgment... user replies "proceed".

---

## Phase 5 — Verify-then-fix

Target file: `openspec/changes/2026-05-08-add-tenant-quotas/proposal.md`.
For a spec review, "fix" means editing the spec — not touching any code.

**#1 — APPLY.** Verification source: `openspec/changes/2025-11-01-resource-limits/proposal.md`
uses fixed 60-second windows. Rewrote §4 to specify window size (60 s, wall-clock aligned), reset
trigger (boundary crossing), and boundary-arrival rule (counted against the window it arrives in).

```
Edit: proposal.md §4 — 3 paragraphs rewritten with explicit window definition.
```

**#2 — APPLY.** Verification source: contradiction is self-evident from §3 and §7; correct
semantics (consume at admission, failures count) matches existing `resource-limits`
spec ("admit-then-count, no reclaim on failure"). Deleted §7 decrement sentence; added
clarifying sentence anchoring decrement to §3 admission, noting that failed requests do
consume quota and are not refunded.

```
Edit: proposal.md §7 — deleted conflicting sentence; added clarification.
```

**#3 — APPLY.** Verification source: `CLAUDE.md` §"HTTP Error Path Convention" — every error path
must specify status, body, log level, and event emission. Added "Quota exceeded" subsection to §5:
HTTP 429, `{ "error": "quota_exceeded", "retryAfterSeconds": <N> }`, WARN log, no event.

```
Edit: proposal.md §5 — added "Quota exceeded" subsection.
```

---

## Phase 6 — Build / test verify

`target=spec` → non-code artifact. No `*.sln` or other build manifest applies.

```
Spec target detected — build/test step skipped (non-code artifact).
```

Spec-level validation still applies. `CLAUDE.md` documents `openspec validate <change-name>`:

```
openspec validate 2026-05-08-add-tenant-quotas
✓ Schema valid
✓ All required sections present
✓ No broken internal references
```

Validation passed.

---

## Phase 7 — Commit

```
git add openspec/changes/2026-05-08-add-tenant-quotas/proposal.md
git commit -m "Review round 1: Fix rate-limit algorithm, §3/§7 contradiction, missing quota-exceeded error path"
```

---

## Phase 8 — Stop

`--rounds=1` → rounds used (1) equals max (1). Stop verdict: **stop-max-rounds**.

> Note: `stop-max-rounds` is correct here even though all Blocker/Critical/High findings were
> addressed. `stop-clean` requires the re-review pass to have confirmed no issues remain in the
> fix diff (Phase 8 rule). With a single round there is no re-review, so the loop cannot confirm
> clean — `stop-max-rounds` is the accurate verdict.

---

## Phase 9 — Final summary (printed to chat — single cycle, no `--save-reports`)

```
## Review Loop Complete

Rounds: 1 of 1 max
Build: skipped (spec target — no compile command)
Tests: not run
Spec validation: passing (openspec validate 2026-05-08-add-tenant-quotas)
Stop verdict: stop-max-rounds

### Round 1 (spec: openspec/changes/2026-05-08-add-tenant-quotas/proposal.md)
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

OpenSpec change proposal adding per-tenant quota enforcement via a sliding-window rate limiter.
412 lines; covers algorithm, error handling, and API contract. Three spec-correctness issues fixed.

## Summary table

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|---|---|---|---|---|
| 1 | Blocker | Spec | proposal.md:§4 | Window size, reset semantics, boundary behavior all undefined | Define window size, reset trigger, and boundary rule explicitly |
| 2 | Critical | Spec | proposal.md:§3 + §7 | Pre-dispatch check (§3) contradicts post-success decrement (§7) | Delete §7 sentence; anchor decrement to §3 admission (failures count, no refund) |
| 3 | High | Spec | proposal.md:§5 | No observable response defined for quota-exceeded | Add HTTP 429, body schema, log level, event rule |
| 4 | Medium | Spec | proposal.md:§2 | "should typically" makes enforcement layer non-normative | Replace with MUST statement naming the mandatory layer |

## Details per item

### 1 Undefined rate-limiting algorithm (§4)

- **Problem:** §4 says "within a sliding window" but gives no window size, reset semantics, or
  boundary-arrival rule. Three implementers would produce three incompatible counters.
- **Impact:** Correct implementation is impossible without guessing at window semantics.
- **Recommendation:** Specify window size (60 s, fixed), reset trigger (window boundary), and
  boundary rule (request counted against the window it arrives in).
- **Verification source:** `openspec/changes/2025-11-01-resource-limits/proposal.md` —
  existing quota design uses fixed 60-second windows; align with that precedent.

### 2 §3 vs §7 contradiction on decrement timing

- **Problem:** §3 checks quota before dispatch; §7 decrements ONLY after a successful response —
  so a failed request costs nothing and does not drain the quota counter. Under sustained failure
  rates, actual throughput can far exceed the intended limit.
- **Impact:** High-failure workloads bypass quota enforcement; rate limiting is ineffective when
  error rates are elevated.
- **Recommendation:** Delete §7 decrement sentence; add note that decrement occurs at §3 admission
  and failed requests consume quota and are not refunded (admit-then-count, no reclaim on failure).
- **Verification source:** `resource-limits` spec — same admit-then-count, no reclaim on
  failure.

### 3 Missing quota-exceeded error path (§5)

- **Problem:** §5 lists timeouts and auth failures but is silent on quota-exceeded: no HTTP
  status, no response body, no log entry, no event emission.
- **Impact:** Implementations diverge; client libraries and dashboards have nothing to pattern-match.
- **Recommendation:** Add "Quota exceeded" subsection: HTTP 429, `{ "error": "quota_exceeded",
  "retryAfterSeconds": N }`, WARN log with entity ID and limit, no event emitted.
- **Verification source:** `CLAUDE.md` §"HTTP Error Path Convention."

### 4 Non-normative enforcement-layer statement (§2)

- **Problem:** "should typically be enforced at the gateway layer" — "should typically" is not
  normative; service-layer enforcement is compliant under this wording.
- **Impact:** Architectural divergence between services implementing this spec.
- **Recommendation:** Replace with "MUST be implemented at the gateway layer." If service-layer
  is also acceptable, say so explicitly.
- **Verification source:** unverified — design preference; flag for author to confirm intent.

## Conclusion

- **Must fix before merge** — #1, #2, #3
- **Acceptable risks** — none
- **Needs discussion** — #4 (author to confirm enforcement-layer normative intent)

## Final verdict

✅➕ **Approve with suggestions** — Blocker, Critical, and High resolved; one Medium (#4) deferred.

## Reviewer model

Review made by `claude-opus-4-7`
