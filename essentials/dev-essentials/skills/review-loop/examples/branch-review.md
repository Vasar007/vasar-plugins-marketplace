# Branch Review — End-to-End Worked Example

The feature branch `feature/<username>/tasks/1234567-add-pagination` is 5 commits ahead of `main` and touches 4 .NET files. The run has two rounds, the `dual` reviewer, and an explicit `--skip=medium,low,nit`.

**Invocation:**

```text
/review-loop target=branch --rounds=2 --reviewer=dual --base=main --skip=medium,low,nit --interactive
```

---

## Phase 1 — Resolve target

The skill runs:

```bash
git diff origin/main...HEAD --stat
```

Output:

```text
 Sources/<example-repo>.Application/Workload/Tenants/Services/TenantQueryService.cs   | 87 +++++++++++-
 Sources/<example-repo>.Application/Workload/Tenants/Queries/GetTenantsQuery.cs       | 34 +++++
 Sources/<example-repo>.Infrastructure/Persistence/Repositories/TenantRepository.cs  | 61 +++++++--
 Sources/<example-repo>.Application.Tests/Workload/Tenants/TenantQueryServiceTests.cs | 42 ++++++
 4 files changed, 224 insertions(+), 0 deletions(-)
```

The skill prints in chat:

```text
Target resolved: branch diff main...HEAD
  4 files changed, 224 insertions(+)
  Base: main  Branch: feature/<username>/tasks/1234567-add-pagination
  Commits: 5
```

---

## Phase 2 — Resolve reviewer + fixer

`--reviewer=dual` resolves to `feature-dev:code-reviewer` and `general-purpose` in parallel. The `feature-dev` plugin is installed, so no fallback applies. The run gives no `--fixer`, so the fixer is the default `general-purpose`.

The skill prints:

```text
Reviewer:  dual → feature-dev:code-reviewer + general-purpose (parallel)
Fixer:     general-purpose
```

---

## Phase 3 — Round 1 review

The skill dispatches two reviewer subagents in parallel: both `Agent` calls go in one message, with no `run_in_background`. Both run on the model of `--reviewer-model`. Each prompt holds the Common Rules, the Full format, and the `branch` brief of `references/reviewer-briefs.md`. In the brief, `<BASE>` is `main`, and the round is Round 1.

Reviewer A (`feature-dev:code-reviewer`) reports 4 findings. Reviewer B (`general-purpose`) reports 3 findings. After the merge of duplicates, 2 findings of B are the same as findings of A.

The 5 findings after the merge:

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|----------|------|--------------|--------------|---------------------|
| 1 | Blocker | Performance | `TenantRepository.cs:89` | `GetPagedAsync` loads all rows and then slices them in memory. The query is unbounded on large datasets. | Add `.Skip(offset).Take(pageSize)` to the EF queryable before `ToListAsync` |
| 2 | High | Test | `TenantQueryServiceTests.cs:31` | No test for `pageSize=0` or for a negative offset | Add negative tests with parameters that assert `ArgumentOutOfRangeException` |
| 3 | High | Architecture | `TenantQueryService.cs:44` | The service takes `IServiceScopeFactory` in its constructor and resolves `ITenantRepository` at call time. The reviewer calls this a DI lifetime anti-pattern (captive dependency). | Inject `ITenantRepository` directly. First find out whether the scope-factory pattern is on purpose. |
| 4 | Medium | Maintainability | `GetTenantsQuery.cs:12` | The `PageSize` default of `50` is a magic literal in three places | Move it to a static class `PaginationDefaults` |
| 5 | Low | Style | `TenantQueryService.cs:67` | The method `GetPage` breaks the async naming convention of the repository. The correct name is `GetPageAsync`. | Rename |

---

## Phase 4 — Triage

`--interactive` is set, so the skill prints the triage in chat and waits for the acknowledgment:

```text
Round 1 findings:
  Blocker:  1  (will fix; 1 blocking)
  Critical: 0  (will fix; 0 blocking)
  High:     2  (will fix; 2 blocking)
  Medium:   1  (deferred — --skip medium; 0 blocking)
  Low:      1  (deferred — --skip low; 0 blocking)
  Nit:      0  (deferred — --skip nit; 0 blocking)

Proceeding to verify+fix 3 issues. Deferring 2.
```

Findings #1 to #3 (one Blocker and two Highs) are each `blocking: true` by default. #4 (Medium) and #5 (Low) are `blocking: false`. The explicit `--skip medium,low` defers them, and the text of neither one calls for a higher status.

The user replies: `ok proceed`

---

## Phase 5 — Verify-then-fix

**Step 5a: the reviewer plans**. The skill dispatches the same reviewer subagent that reported the findings again. It proposes a fix plan for each finding that can get a fix, based on existing patterns:

- F1: apply `.Skip().Take()` before `.ToListAsync()`, as the sibling `ExternalResourceRepository.cs` does.
- F2: add negative tests with `foreach` over a `List<Action>`, as `dotnet-backend-dev:create-tests` documents for null-argument guards.
- F3: before any fix, compare the finding with the `IServiceScopeFactory` usage in `BaseWorker.cs`.

**Step 5b: the fixer carries out the plan**. The fixer subagent (`general-purpose`) classifies the three findings that the triage cleared before it touches any file. It works from the plan of the reviewer and does not choose its own approach from scratch.

**F1 [APPLY]**. Proved: `TenantRepository.cs:89` calls `await context.Tenants.ToListAsync()` and then `.Skip().Take()` on the result in memory. A known working EF pattern in the sibling service (`ExternalResourceRepository.cs:54`) applies `.Skip().Take()` on the `IQueryable` before the query runs. The fix stays inside lines 87 to 93.

**F2 [PARTIAL]**. The gap in the test shape is real: `TenantQueryServiceTests.cs` has no test for `pageSize=0` or for a negative `offset`. The fixer read `TenantQueryService.cs:38` to scope the fix. The service leaves the input guard to the repository layer, as other services in this codebase do. So the finding is about missing test coverage, not about a missing runtime guard. The reviewer suggested `[TestCase]` attribute tests. But `dotnet-backend-dev:create-tests` documents `foreach` over a `List<Action>` for constructor guards and over a `List<Func<Task>>` for method guards. It has no rule for range guards. So the fixer followed the existing guard tests of `TenantRepositoryTests`, which is the working code of the repository. It wrote a `foreach` over a `List<Action>` test that asserts `ArgumentOutOfRangeException`. The `[TestCase]` form is the suggested direction of the reviewer, and the fixer did not adopt it. The finding itself, the missing coverage, is fully resolved.

**F3 [REJECT]**. The reviewer claims that the injection of `IServiceScopeFactory` is a service-locator anti-pattern. The fixer read all of `TenantQueryService.cs`. The service uses `IServiceScopeFactory` to create a short-lived scope for each request. This is the documented pattern to use scoped services from a background-hosted context. `BaseWorker.cs:31` of `BackgroundJobService` uses the same injection of `IServiceScopeFactory`. The fixer rejects the finding, because the code is correct.

```text
F1 [APPLY]   — In-memory slice confirmed at TenantRepository.cs:89; fix bounded to that method.
F2 [PARTIAL] — Missing test coverage confirmed; finding resolved; [TestCase] direction not adopted (create-tests
               documents foreach-over-List<Action> and List<Func<Task>> for null-arg guards; no rule for range guards;
               existing TenantRepositoryTests guard tests followed); foreach test applied.
F3 [REJECT]  — IServiceScopeFactory scope pattern verified correct via BackgroundJobService
               BaseWorker.cs:31; reviewer's claim does not verify against the source.
```

Edited files: `TenantRepository.cs` and `TenantQueryServiceTests.cs`.

---

## Phase 6 — Build / test verify

`CLAUDE.md` documents the command `dotnet build ./Sources/<example-repo>.sln -c Debug`.

```text
dotnet build ./Sources/<example-repo>.sln -c Debug
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

A focused test filter for the files that the fix pass touched:

```text
dotnet test ./Sources/<example-repo>.sln \
  --filter "FullyQualifiedName~TenantQueryServiceTests|FullyQualifiedName~TenantRepositoryTests"

Passed: 24   Failed: 0   Skipped: 0
```

---

## Phase 7 — Commit

```bash
git add Sources/<example-repo>.Infrastructure/Persistence/Repositories/TenantRepository.cs \
        Sources/<example-repo>.Application.Tests/Workload/Tenants/TenantQueryServiceTests.cs

git commit -m "Review round 1: Fix unbounded pagination query and add edge-case tests

TenantRepository.GetPagedAsync now applies Skip/Take on the IQueryable before
materialisation (was slicing an in-memory list). Added foreach-over-List<Action>
tests for pageSize=0 and negative offset."
```

---

## Phase 8 — Repeat

Rounds used: 1. Maximum rounds: 2. The fixer applied edits in this cycle, so the loop continues.

The re-review in Round 2 covers only the 2 files that the fix commit changed. The re-review uses one `general-purpose` agent on `--reviewer-model`, as Phase 8 of `SKILL.md` says. The reviewer setup of the run (`dual`) applies only to Round 1.

The re-review brief is the `branch` brief of `references/reviewer-briefs.md`, with the scope narrowed to the fix diff and the round set to 2.

The agent reports no new findings. Both applied fixes look correct, and it sees no regression.

**Phase 6 in Round 2**: Round 2 found no issues, so the fixer made no edit in Round 2. So Phase 6 does not run again in Round 2. The build and test status of Round 1 carries forward into Phase 9.

---

## Phase 9 — Final summary

Two cycles ran. So the summary goes to `Notes/Reviews/branch-1234567-add-pagination-summary.md` (the destination rule for a run with more than one cycle).

```markdown
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

```text
Cycle 1 — branch diff main...HEAD (4 files, 224 insertions)
  5 findings: 1 Blocker, 0 Critical, 2 High, 1 Medium, 1 Low, 0 Nit
  Triage: fix=3, deferred=2 (per --skip medium,low,nit / merit triage)
  Fix verdicts: APPLY=1, PARTIAL=1, REJECT=1
  Build: pass
  Tests: 24 passed, 0 failed, 0 skipped
  Verdict: continue
```

**After Round 2:**

```text
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

The skill writes this report to `Notes/Reviews/branch-1234567-add-pagination-cycle-1.md`.

---

# Review by AI Agent (Round-1) — branch diff main...HEAD

## Description

Adds cursor-based pagination to `TenantQueryService` and `TenantRepository` through a new `GetTenantsQuery` model. 4 files changed, with 224 insertions.

## Summary table

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|----------|------|--------------|--------------|---------------------|
| 1 | Blocker | Performance | `TenantRepository.cs:89` | `GetPagedAsync` loads the full table into memory before it slices it | Apply `.Skip(offset).Take(pageSize)` to the `IQueryable` before `ToListAsync` |
| 2 | High | Test | `TenantQueryServiceTests.cs:31` | No coverage for `pageSize=0` or a negative `offset`. The service passes the bounds to the repository, which is the guard layer, but that path has no tests. | Add tests with negative input that assert `ArgumentOutOfRangeException` |
| 3 | High | Architecture | `TenantQueryService.cs:44` | The service injects `IServiceScopeFactory` to resolve the repository at call time. The reviewer calls this a DI anti-pattern. | Compare with the scope-factory pattern before any action |
| 4 | Medium | Maintainability | `GetTenantsQuery.cs:12` | The magic literal `50` for the default page size is in three places | Move it to a constant class `PaginationDefaults` |
| 5 | Low | Style | `TenantQueryService.cs:67` | A method named `GetPage` in a codebase with an async naming convention | Rename it to `GetPageAsync` |

## Details per item

### 1 Blocker — GetPagedAsync loads all rows before slicing

- **Problem**: `TenantRepository.cs:89` calls `await context.Tenants.ToListAsync()` and then applies `.Skip(offset).Take(pageSize)` on the returned `List<TenantEntity>`. Each request for a page loads every row of the table into memory.
- **Impact**: on a large table, each list call scans the full table and allocates O(n) memory, and queries time out under load.
- **Recommendation**: move `.Skip(offset).Take(pageSize)` before `.ToListAsync()`, so that EF translates them to the SQL clauses `OFFSET` and `FETCH`.
- **Verification source**: F1 [APPLY]. The slice in memory is real, at `TenantRepository.cs:89`. The fix stays inside lines 87 to 93. The pattern matches `ExternalResourceRepository.cs:54`, a known working example in a sibling service.

### 2 High — Missing edge-case tests for pageSize=0 and negative offset

- **Problem**: `TenantQueryServiceTests.cs` has no coverage for `pageSize=0` or for a negative `offset`. The fixer read `TenantQueryService.cs:38`. The service leaves validation to the repository layer: it passes the bounds to the repository, and the repository does the guard. So the finding is about missing test coverage, not about a missing runtime guard.
- **Impact**: inputs at the edges have no test coverage, so a regression in the guard behavior goes unnoticed.
- **Recommendation**: add tests with `foreach` over a `List<Action>` that assert `ArgumentOutOfRangeException` for `pageSize=0` and `offset=-1`.
- **Verification source**: F2 [PARTIAL]. The gap is real, from a read of `TenantQueryService.cs:38`. The test uses `foreach` over a `List<Action>`. `dotnet-backend-dev:create-tests` documents this pattern for constructor guards and over a `List<Func<Task>>` for method guards. It has no rule for range guards, so the fixer followed the existing guard tests of `TenantRepositoryTests` and did not adopt the `[TestCase]` direction. The finding itself, the missing coverage, is fully resolved.

### 3 High — IServiceScopeFactory injection claimed as DI anti-pattern

- **Problem**: the reviewer says that `TenantQueryService` injects `IServiceScopeFactory` and resolves `ITenantRepository` in the method body. The reviewer calls this a "service locator anti-pattern".
- **Impact**: claimed, a leak of a scoped service or a hidden dependency.
- **Recommendation**: see the verification source. The finding is rejected.
- **Verification source**: F3 [REJECT]. The fixer read all of `TenantQueryService.cs`. The service injects `IServiceScopeFactory` and creates a scoped lifetime for each call. This is the documented pattern to use scoped services from background hosts with a singleton lifetime. `BaseWorker.cs:31` of `BackgroundJobService` is a known working example of the same pattern. The claim of the reviewer does not hold against the source, so the finding is rejected.

### 4 Medium — Magic literal 50 for default page size

- **Problem**: the value `50` is a bare integer literal in `GetTenantsQuery.cs:12`, `TenantQueryService.cs:21`, and `TenantRepository.cs:14`.
- **Impact**: a reader cannot tell that the three literals are the same constant. A change of the default needs three edits, and the compiler does not keep them the same.
- **Recommendation**: move it to a constant `PaginationDefaults.DefaultPageSize`. Deferred by `--skip medium`.
- **Verification source**: deferred. No fix in this cycle.

### 5 Low — GetPage not suffixed with Async

- **Problem**: `TenantQueryService.cs:67` declares `public Task<PagedResult<TenantDto>> GetPage(...)`. The async naming convention of the repository requires the suffix `Async` on every method that returns a `Task`.
- **Impact**: the name does not follow the naming convention, and an analyzer can warn about it later.
- **Recommendation**: rename it to `GetPageAsync`. Deferred by `--skip low`.
- **Verification source**: deferred. No fix in this cycle.

## Conclusion

- **Must fix before merge**: #1, #2
- **Acceptable risks**: #3 (the finding is rejected, and the code is correct)
- **Needs discussion**: _(none)_

## Final verdict

✅➕ **Approve with suggestions**. This cycle's fix pass handled the Blocker and the High findings that had a valid fix (F1 APPLY, F2 PARTIAL, F3 REJECT as correct). The deferred Medium and Low items do not block the merge, but keep track of them.

## Reviewer model

Review made by `claude-opus-4-7`
Review made by `claude-opus-4-7`
