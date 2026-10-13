# Branch Review — End-to-End Worked Example

Feature branch `feature/<username>/tasks/1234567-add-pagination`, 5 commits ahead of `main`,
touching 4 .NET files. Two rounds, dual reviewer, explicit `--skip=medium,low,nit`.

**Invocation:**

```text
/review-loop target=branch --rounds=2 --reviewer=dual --base=main --skip=medium,low,nit --interactive
```

---

## Phase 1 — Resolve target

The skill runs:

```
git diff origin/main...HEAD --stat
```

Output:

```
 Sources/<example-repo>.Application/Workload/Tenants/Services/TenantQueryService.cs   | 87 +++++++++++-
 Sources/<example-repo>.Application/Workload/Tenants/Queries/GetTenantsQuery.cs       | 34 +++++
 Sources/<example-repo>.Infrastructure/Persistence/Repositories/TenantRepository.cs  | 61 +++++++--
 Sources/<example-repo>.Application.Tests/Workload/Tenants/TenantQueryServiceTests.cs | 42 ++++++
 4 files changed, 224 insertions(+), 0 deletions(-)
```

Skill prints to chat:

```
Target resolved: branch diff main...HEAD
  4 files changed, 224 insertions(+)
  Base: main  Branch: feature/<username>/tasks/1234567-add-pagination
  Commits: 5
```

---

## Phase 2 — Resolve reviewer + fixer

`--reviewer=dual` resolves to `feature-dev:code-reviewer` + `general-purpose` in parallel.
`feature-dev` plugin is installed — no fallback triggered.
`--fixer` not specified — defaults to `general-purpose`.

Skill prints:

```
Reviewer:  dual → feature-dev:code-reviewer + general-purpose (foreground-parallel)
Fixer:     general-purpose
```

---

## Phase 3 — Round 1 review

Two reviewer subagents dispatched in foreground-parallel (both Agent calls in one assistant
message, no `run_in_background`). Each receives the branch brief from `references/reviewer-briefs.md`:

> **Scope:** `git diff origin/main...HEAD`. Diff provided below.
> **Round:** Round 1 — use this value; do not infer from conversation.
>
> You are a code reviewer. Find real problems, not a list of everything you noticed.
>
> **Focus areas (priority order):**
> 1. **Bugs and logic errors** — read the actual changed files in context, not just diff hunks.
>    Cross-file consequences are invisible from the diff alone; load files the changed code calls.
> 2. **Security** — injection, credential exposure, broken auth, unsafe deserialization, CORS bypass.
> 3. **Data integrity** — broken FK relationships, silent truncation, lost updates, non-atomic ops.
> 4. **Performance** — N+1 queries, unbounded collection loads, synchronous I/O blocking the pool.
> 5. **DI lifetime** — scoped service captured in singleton, transient EF context in wrong lifetime.
> 6. **Contract breaks** — REST API shape changes, interface violations, event schema changes.
> 7. **Test coverage** — untested critical paths, assertions that don't verify anything meaningful.
>
> **Coherence check (mandatory):** verify changes are coherent across commits. A later commit may
> mask a regression introduced earlier — read `git log origin/main..HEAD` to check the commit sequence.
>
> Apply common rules.

Reviewer A (`feature-dev:code-reviewer`) reports 4 findings.
Reviewer B (`general-purpose`) reports 3 findings; 2 overlap with Reviewer A after deduplication.

Deduplicated findings — 5 total:

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|----------|------|--------------|--------------|---------------------|
| 1 | Blocker | Performance | `TenantRepository.cs:89` | `GetPagedAsync` loads all rows then slices in memory — unbounded query on large datasets | Add `.Skip(offset).Take(pageSize)` to the EF queryable before `ToListAsync` |
| 2 | High | Test | `TenantQueryServiceTests.cs:31` | No test for `pageSize=0` or negative offset | Add parameterised negative tests asserting `ArgumentOutOfRangeException` |
| 3 | High | Architecture | `TenantQueryService.cs:44` | Service takes `IServiceScopeFactory` in constructor to resolve `ITenantRepository` at call time — claimed DI lifetime anti-pattern (captive dependency) | Inject `ITenantRepository` directly; verify whether scope-factory pattern is intentional |
| 4 | Medium | Maintainability | `GetTenantsQuery.cs:12` | `PageSize` default of `50` is a magic literal repeated in three places | Extract to a `PaginationDefaults` static class |
| 5 | Low | Style | `TenantQueryService.cs:67` | Method `GetPage` should be `GetPageAsync` per repo async naming convention | Rename |

---

## Phase 4 — Triage

Skill prints to chat and waits for acknowledgment (`--interactive` is set):

```
Round 1 findings:
  Blocker:  1  (will fix; 1 blocking)
  Critical: 0  (will fix; 0 blocking)
  High:     2  (will fix; 2 blocking)
  Medium:   1  (deferred — --skip medium; 0 blocking)
  Low:      1  (deferred — --skip low; 0 blocking)
  Nit:      0  (deferred — --skip nit; 0 blocking)

Proceeding to verify+fix 3 issues. Deferring 2.
```

Findings #1–#3 (Blocker/2×High) are each `blocking: true` by default. #4 (Medium) and #5 (Low) are
`blocking: false` — deferred via the explicit `--skip medium,low` and neither one's text warrants
elevation.

User replies: `ok proceed`

---

## Phase 5 — Verify-then-fix

**Step 5a — reviewer plans.** The same Opus reviewer subagent that reported the findings is
dispatched again to propose a fix plan for each fixable finding, grounded in existing patterns:
for F1, apply `.Skip().Take()` before `.ToListAsync()`, matching the sibling
`ExternalResourceRepository.cs` pattern; for F2, add `foreach`-over-`List<Action>` negative tests
per the constructor-null-arg-tests convention; F3 should first be re-verified against
`BaseWorker.cs`'s `IServiceScopeFactory` usage before any fix is attempted.

**Step 5b — fixer implements.** The fixer subagent (`general-purpose`) classifies all five findings
before touching any file, implementing against the reviewer's plan rather than deciding its own
approach from scratch.

**F1 [APPLY]** — Confirmed: `TenantRepository.cs:89` calls `await context.Tenants.ToListAsync()` then
`.Skip().Take()` on the in-memory result. Known-working EF pattern (sibling service
`ExternalResourceRepository.cs:54`) applies `.Skip().Take()` on the `IQueryable`
before materialisation. Fix is bounded to lines 87–93.

**F2 [PARTIAL]** — Test-shape gap confirmed: `TenantQueryServiceTests.cs` has no coverage for
`pageSize=0` or negative `offset` inputs. Fixer read `TenantQueryService.cs:38` to scope the fix
and confirmed the service delegates validation to the repository layer (consistent with other
services in this codebase), so input-guard responsibility belongs at the repository layer and the
finding is scoped to missing test coverage, not a missing runtime guard. The reviewer suggested
`[TestCase]` attribute tests; the `foreach`-over-`List<Action>` pattern is the documented
convention for **constructor null-argument tests** specifically (see
`dotnet-backend-dev:create-tests` examples); other negative-test patterns (e.g., string-validation
tests) may legitimately use `[TestCaseSource]`. Applied as a `foreach`-over-`List<Action>` test
asserting `ArgumentOutOfRangeException`; `[TestCase]` boolean-stripes form rejected for this
pattern.

**F3 [REJECT]** — Reviewer claims `IServiceScopeFactory` injection is a service-locator anti-pattern. Fixer reads
`TenantQueryService.cs` in full: `IServiceScopeFactory` is used to create a short-lived scope per request — this is the documented pattern for consuming
scoped services from a background-hosted context. Cross-referenced `BackgroundJobService`
`BaseWorker.cs:31` which uses identical `IServiceScopeFactory` injection. Finding rejected;
the code is correct.

```
F1 [APPLY]   — In-memory slice confirmed at TenantRepository.cs:89; fix bounded to that method.
F2 [PARTIAL] — Missing test coverage confirmed; [TestCase] boolean-stripes form rejected (the
               foreach-over-List<Action> pattern is the convention for constructor null-arg tests
               per create-tests skill examples; other negative tests may use [TestCaseSource]);
               foreach test applied.
F3 [REJECT]  — IServiceScopeFactory scope pattern verified correct via BackgroundJobService
               BaseWorker.cs:31; reviewer's claim does not verify against the source.
```

Files edited: `TenantRepository.cs`, `TenantQueryServiceTests.cs`.

---

## Phase 6 — Build / test verify

`CLAUDE.md` documents: `dotnet build ./Sources/<example-repo>.sln -c Debug`.

```
dotnet build ./Sources/<example-repo>.sln -c Debug
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

Focused test filter (files touched by the fix pass):

```
dotnet test ./Sources/<example-repo>.sln \
  --filter "FullyQualifiedName~TenantQueryServiceTests|FullyQualifiedName~TenantRepositoryTests"

Passed: 24   Failed: 0   Skipped: 0
```

---

## Phase 7 — Commit

```
git add Sources/<example-repo>.Infrastructure/Persistence/Repositories/TenantRepository.cs \
        Sources/<example-repo>.Application.Tests/Workload/Tenants/TenantQueryServiceTests.cs

git commit -m "Review round 1: Fix unbounded pagination query and add edge-case tests

TenantRepository.GetPagedAsync now applies Skip/Take on the IQueryable before
materialisation (was slicing an in-memory list). Added foreach-over-List<Action>
tests for pageSize=0 and negative offset."
```

---

## Phase 8 — Repeat

Rounds used: 1. Rounds max: 2. Fixer applied edits this cycle: yes. Continue.

Round 2 re-review scope: only the 2 files changed in the fix commit. Reviewer for re-review:
single `general-purpose` agent (per SKILL.md Phase 8 rule — full reviewer/fixer config applies
only to Round 1).

Re-review brief passed to the agent: branch brief from `references/reviewer-briefs.md` with
scope narrowed to the fix diff only and Round set to 2.

Agent reports: no new findings. Both applied fixes look correct; no regressions visible.

**Phase 6 in Round 2:** the fixer applied edits this cycle (2 files changed in Phase 5), so
Phase 6 re-runs against those 2 files — build and focused test filter both pass (see outputs
below). If the fixer had applied zero edits (all findings REJECT), Phase 6 would be skipped
and the previous cycle's build/test status carried forward into Phase 9.

---

## Phase 9 — Final summary

Two cycles ran — report written to
`Notes/Reviews/branch-1234567-add-pagination-summary.md` (multi-cycle destination rule).

```
## Review Loop Complete

Rounds: 2 of 2 max
Build: passing (0 errors, 0 warnings)
Tests: 24 passed, 0 failed, 0 skipped
Stop verdict: stop-clean

### Round 1 (branch diff main...HEAD — 4 files, 224 insertions)
  Found:    1 Blocker, 0 Critical, 2 High, 1 Medium, 1 Low, 0 Nit
  Fixed:    2 (APPLY=1, PARTIAL=1, REJECT=1)
  Deferred: 2 (per --skip medium,low / merit triage)

### Round 2 (re-review of fix diff — 2 files)
  Found: 0 issues
  Status: clean

### Deferred items (by severity; (blocking) = Phase 4 marked it must-fix-before-merge)
  [Medium] 4: Magic literal PageSize=50 repeated in three places — extract to PaginationDefaults
  [Low]    5: Method GetPage should be GetPageAsync (async naming convention)

### Rejected findings
  1 REJECT: F3 — IServiceScopeFactory scope pattern is correct per BaseWorker.cs:31; not an anti-pattern.
```

---

## Brief format — as printed after each cycle

**After Round 1:**

```
Cycle 1 — branch diff main...HEAD (4 files, 224 insertions)
  5 findings: 1 Blocker, 0 Critical, 2 High, 1 Medium, 1 Low, 0 Nit
  Triage: fix=3, deferred=2 (per --skip medium,low,nit / merit triage)
  Fix verdicts: APPLY=1, PARTIAL=1, REJECT=1
  Build: pass
  Tests: 24 passed, 0 failed, 0 skipped
  Verdict: continue
```

**After Round 2:**

```
Cycle 2 — re-review of fix diff (2 files)
  0 findings: 0 Blocker, 0 Critical, 0 High, 0 Medium, 0 Low, 0 Nit
  Triage: fix=0, deferred=0
  Fix verdicts: APPLY=0, PARTIAL=0, REJECT=0
  Build: pass
  Tests: 24 passed, 0 failed, 0 skipped
  Verdict: stop-clean
```

---

## Full format — Round 1 report

Written to `Notes/Reviews/branch-1234567-add-pagination-cycle-1.md`.

---

# Review by AI Agent (Round-1) — branch diff main...HEAD

## Description

Adds cursor-based pagination to `TenantQueryService` and `TenantRepository` via a new
`GetTenantsQuery` model; 4 files changed, 224 insertions.

## Summary table

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|----------|------|--------------|--------------|---------------------|
| 1 | Blocker | Performance | `TenantRepository.cs:89` | `GetPagedAsync` loads the full table into memory before slicing | Apply `.Skip(offset).Take(pageSize)` to the `IQueryable` before `ToListAsync` |
| 2 | High | Test | `TenantQueryServiceTests.cs:31` | No coverage for `pageSize=0` or negative `offset`; the service forwards bounds to the repository, which is the guard layer, but that path has no tests | Add negative-input tests asserting `ArgumentOutOfRangeException` |
| 3 | High | Architecture | `TenantQueryService.cs:44` | Service injects `IServiceScopeFactory` to resolve repository at call time — claimed DI anti-pattern | Verify against scope-factory pattern before acting |
| 4 | Medium | Maintainability | `GetTenantsQuery.cs:12` | Magic literal `50` for default page size repeated in three locations | Extract to `PaginationDefaults` constant class |
| 5 | Low | Style | `TenantQueryService.cs:67` | Method named `GetPage` in an async-convention codebase | Rename to `GetPageAsync` |

## Details per item

### 1 Blocker — GetPagedAsync loads all rows before slicing

- **Problem:** `TenantRepository.cs:89` calls `await context.Tenants.ToListAsync()` then applies
  `.Skip(offset).Take(pageSize)` on the returned `List<TenantEntity>`. This materialises every
  row in the table on every paginated request.
- **Impact:** On a large table this causes full-table scans on every list call, O(n) memory
  allocations per request, and query timeouts under load.
- **Recommendation:** Move `.Skip(offset).Take(pageSize)` before `.ToListAsync()` so EF translates
  them to SQL `OFFSET`/`FETCH` clauses.
- **Verification source:** F1 [APPLY] — In-memory slice confirmed at `TenantRepository.cs:89`; fix
  bounded to lines 87–93. Pattern verified against `ExternalResourceRepository.cs:54`
  (known-working example in sibling service).

### 2 High — Missing edge-case tests for pageSize=0 and negative offset

- **Problem:** `TenantQueryServiceTests.cs` has no coverage for `pageSize=0` or negative `offset`
  inputs. The fixer read `TenantQueryService.cs:38` and confirmed validation is delegated to the
  repository layer (the service correctly forwards bounds to the repo, which is the layer that
  performs the guard). The finding is scoped to the missing test coverage, not a missing runtime
  guard.
- **Impact:** Edge-case inputs have no test coverage; regressions in guard behaviour would go
  undetected.
- **Recommendation:** Add `foreach`-over-`List<Action>` tests asserting `ArgumentOutOfRangeException`
  for `pageSize=0` and `offset=-1`.
- **Verification source:** F2 [PARTIAL] — Gap confirmed by reading `TenantQueryService.cs:38`.
  Applied as `foreach`-over-`List<Action>` pattern — the documented convention for **constructor
  null-argument tests** (see `dotnet-backend-dev:create-tests` skill examples). Note: other
  negative-test patterns (e.g., string-validation tests) may legitimately use `[TestCaseSource]`;
  the restriction to `List<Action>` applies specifically to constructor null-argument guard tests.
  `[TestCase]` boolean-stripes form rejected for this pattern.

### 3 High — IServiceScopeFactory injection claimed as DI anti-pattern

- **Problem:** Reviewer flags that `TenantQueryService` injects `IServiceScopeFactory` and resolves
  `ITenantRepository` inside the method body, describing this as a "service locator anti-pattern".
- **Impact:** Claimed: scoped service leak or hidden dependency coupling.
- **Recommendation:** See verification source — finding rejected.
- **Verification source:** F3 [REJECT] — Fixer read `TenantQueryService.cs` in full. The service
  injects `IServiceScopeFactory` and creates a scoped lifetime per call — the documented pattern
  for consuming scoped services from singleton-lifetime background hosts. Cross-referenced
  `BackgroundJobService` `BaseWorker.cs:31` (known-working example). Reviewer's claim does
  not verify against the source; finding rejected.

### 4 Medium — Magic literal 50 for default page size

- **Problem:** The value `50` appears as a bare integer literal in `GetTenantsQuery.cs:12`,
  `TenantQueryService.cs:21`, and `TenantRepository.cs:14`.
- **Impact:** A reader cannot tell the three literals are the same constant; changing the default
  requires three edits with no compile-time guarantee of consistency.
- **Recommendation:** Extract to a `PaginationDefaults.DefaultPageSize` constant. Deferred per
  `--skip medium`.
- **Verification source:** deferred — no fix applied this cycle.

### 5 Low — GetPage not suffixed with Async

- **Problem:** `TenantQueryService.cs:67` declares `public Task<PagedResult<TenantDto>> GetPage(...)`.
  The repo async naming convention requires the `Async` suffix on all `Task`-returning methods.
- **Impact:** Inconsistency with the naming convention; potential future analyser warning.
- **Recommendation:** Rename to `GetPageAsync`. Deferred per `--skip low`.
- **Verification source:** deferred — no fix applied this cycle.

## Conclusion

- **Must fix before merge** — #1, #2
- **Acceptable risks** — #3 (finding rejected; code is correct)
- **Needs discussion** — _(none)_

## Final verdict

✅➕ **Approve with suggestions** — Blocker and fixable High findings addressed in this cycle's fix
pass (F1 APPLY, F2 PARTIAL, F3 REJECT-correct). Deferred Medium and Low items are not
merge-blocking but should be tracked.

## Reviewer model

Review made by `claude-sonnet-4-6`
Review made by `claude-sonnet-4-6`
