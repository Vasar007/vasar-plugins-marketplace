# Triage Matrix — Severity → Action Mapping

Referenced by Phase 4 of `SKILL.md`. All severity and type tokens used in this file match
the parameter table in `SKILL.md` verbatim. Do not invent new tokens.

---

## Severity scale

### Blocker

Will not merge / will not ship — data loss, security holes, broken contracts, crashes. Examples:
SQL injection or auth bypass that leaks data, a migration that silently drops or truncates a column
with live data, a broken public contract (REST response shape change that destroys consumers), an
unhandled exception that crashes the service on startup. Fix before anything else is discussed.

### Critical

Must fix before merge. Examples: business-logic error that produces wrong totals or routes requests
to the wrong destination, missing error handling on a path that corrupts state on failure, a race
condition that loses writes under concurrent load. The impact is significant and the fix is
unambiguous — these are not theories.

### High

Should fix before merge. Examples: N+1 query inside a per-row loop, an assumption that an external
call always succeeds with no retry or circuit-break, a critical code path with zero test coverage,
a DI lifetime mismatch (scoped service injected into singleton). Leaving these in creates real
operational risk, but the service remains functional.

### Medium

Quality issue. Examples: a pattern violation that is consistent throughout the codebase but wrong
(e.g. manual string formatting where a helper exists), a minor coverage gap on a non-critical path,
a cleanup opportunity that improves readability without changing behaviour. Skip by default.

### Low

Nice-to-have. Examples: a minor refactoring that shortens a method, renaming a variable to better
reflect its purpose, extracting a repeated literal into a constant. No operational impact. Skip by
default.

### Nit

Style only. Examples: wrong indentation, a trailing space, a comment that duplicates the code,
inconsistent capitalisation in a log message. Zero semantic impact. Skip by default.

---

## Default `--skip` value and token rules

**Default:** `--skip medium,low,nit`

Each token in `--skip` is independent. `--skip medium,low` defers Medium and Low but Nit is still
eligible for fixing. Valid tokens: `blocker`, `critical`, `high`, `medium`, `low`, `nit`. Token
`none` is a special value meaning "skip nothing — fix every severity".

---

## Action mapping

| Severity | Default action | Rationale |
|----------|---------------|-----------|
| Blocker  | **Fix now**   | Never merge with one unresolved. |
| Critical | **Fix now**   | Significant impact; fix is clear. |
| High     | **Fix now**   | Real operational risk; addressable in a normal fix pass. |
| Medium   | **Deferred (default)** | Quality issue; does not block shipping. |
| Low      | **Deferred (default)** | Nice-to-have; no operational impact. |
| Nit      | **Deferred (default)** | Style only; zero semantic impact. |

---

## Triage-presentation format (Phase 4)

Print this block after collecting all reviewer output, before any fix is applied. Wait for user
acknowledgment unless `--auto-proceed` is set.

```text
Round <N> findings:
  Blocker:  <X>  (will fix)
  Critical: <X>  (will fix)
  High:     <X>  (will fix)
  Medium:   <X>  (deferred — --skip medium)
  Low:      <X>  (deferred — --skip low)
  Nit:      <X>  (deferred — --skip nit)

Proceeding to verify+fix <F> issues. Deferring <D>.
```

Rows whose severity is in `--skip` show "(deferred — --skip `<token>`)". Rows whose severity is
not in `--skip` show "(will fix)". When `--skip none`, every row shows "(will fix)" and no deferred
annotation appears.

---

## `--skip` interaction matrix

| `--skip` value | Severities fixed now | Severities deferred |
|----------------|---------------------|---------------------|
| `none` | Blocker, Critical, High, Medium, Low, Nit | _(none)_ |
| `nit` | Blocker, Critical, High, Medium, Low | Nit |
| `low,nit` | Blocker, Critical, High, Medium | Low, Nit |
| `medium,low,nit` _(default)_ | Blocker, Critical, High | Medium, Low, Nit |
| `critical,high,medium,low,nit` | Blocker only | Critical, High, Medium, Low, Nit |
| `blocker` | Critical, High, Medium, Low, Nit | Blocker (deferred to a follow-up cycle; use only when shipping known-broken code intentionally) |

Any subset of the six tokens is valid. Each omitted token is eligible for fixing; each included
token is deferred. The matrix rows above are illustrative examples, not the exhaustive set.

---

## Type taxonomy

One type per finding. Use these exact tokens in every report table and phase output.

| Type | Definition |
|------|------------|
| `Bug` | Incorrect behaviour — wrong output, wrong state, wrong control flow. |
| `Reliability` | Code that works today but fails under error, load, or concurrency (missing retries, unbounded collections, unhandled exceptions). |
| `Security` | Injection, credential exposure, broken auth/authz, missing input validation, insecure defaults. |
| `Performance` | N+1 queries, unnecessary allocations, missing pagination, synchronous blocking in async paths. |
| `Maintainability` | Code that is correct but unnecessarily hard to change (deep nesting, magic literals, duplicated logic, misleading names). |
| `Test` | Missing coverage of critical paths, assertions that do not actually verify the contract, flaky setup. |
| `Style` | Formatting, naming conventions, whitespace — no semantic impact. |
| `Architecture` | Cross-cutting structural issues: DI lifetime mismatches, layer violations, wrong abstractions, broken contracts between components. |
| `Spec` | Finding in a spec, design doc, or OpenSpec change (non-code target). |
| `Docs` | Missing, incorrect, or misleading documentation, comments, or changelog entries. |
