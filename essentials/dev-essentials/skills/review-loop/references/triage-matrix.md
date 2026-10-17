# Triage Matrix — Severity → Action Mapping

Phase 4 of `SKILL.md` uses this file. All severity and type tokens in this file are the tokens of the section "Severity and type taxonomy" of `SKILL.md`, word for word. Do not invent new tokens.

---

## Severity scale

### Blocker

The change cannot merge or ship. Examples: data loss, security holes, broken contracts, crashes. More examples: an SQL injection or an auth bypass that leaks data, or a migration that silently drops or truncates a column with live data. Also a broken public contract, such as a change of the REST response shape that breaks the consumers. Also an unhandled exception that crashes the service at startup. Fix a Blocker before anything else.

### Critical

Must be fixed before merge. Examples: a business-logic error that gives wrong totals or sends requests to the wrong destination. Also missing error handling on a path that corrupts state on failure, or a race condition that loses writes under concurrent load. The impact is large and the fix is clear. These findings are not theories.

### High

Fix before merge by default. Examples: an N+1 query inside a loop over rows, or an assumption that an external call always succeeds, with no retry or circuit breaker. Also a critical code path with no test coverage, or a DI lifetime mismatch (a scoped service injected into a singleton). These findings leave a real operational risk, but the service still works.

### Medium

A quality issue. Examples: a pattern violation that is consistent across the codebase but wrong, such as manual string formatting where a helper exists. Also a small coverage gap on a path that is not critical. Also a cleanup that makes the code easier to read, with no change of behavior. A Medium is not deferred automatically by its label. Phase 4 judges it on its merits. A Medium still gets a fix in two cases: it brings back a variant of the bug under repair, or it leaves the regression of the fix without test coverage.

### Low

Nice to have. Examples: a small refactor that shortens a method, a better name for a variable, or a repeated literal moved into a constant. No operational impact. The merit judgment of Phase 4 usually defers a Low, but its label alone does not defer it.

### Nit

Style only. Examples: wrong indentation, a trailing space, a comment that repeats the code, or inconsistent capital letters in a log message. No semantic impact. The merit judgment of Phase 4 usually defers a Nit, but its label alone does not defer it.

---

## Default `--skip` value and token rules

**Default**: `--skip none`. Nothing is deferred by its severity label. Every finding goes to the merit-based triage of Phase 4 instead (see the section "Default configuration" and Phase 4 of `SKILL.md`).

Each token in `--skip` is independent. `--skip medium,low` defers Medium and Low, but a Nit can still get a fix. Valid tokens: `blocker`, `critical`, `high`, `medium`, `low`, `nit`. The token `none` is a special value. It means "skip nothing by label, and triage every severity", and it is the default.

---

## Action mapping

| Severity | Action | Rationale |
|----------|---------------|-----------|
| Blocker  | **Fix now**   | Never merge with an unresolved Blocker. |
| Critical | **Fix now**   | The impact is large, and the fix is clear. |
| High     | **Fix now**   | A real operational risk that a normal fix pass can address. |
| Medium   | **Triage on merit**. Deferred only by a `--skip` that names it, or by the judgment of Phase 4. | A quality issue. It does not block shipping, but it can still be the finding that matters. |
| Low      | **Triage on merit**. Deferred only by a `--skip` that names it, or by the judgment of Phase 4. | Nice to have. Usually no operational impact. |
| Nit      | **Triage on merit**. Deferred only by a `--skip` that names it, or by the judgment of Phase 4. | Style only. Usually no semantic impact. |

---

## The `blocking` flag — severity-independent

Severity orders the triage table and the deferred list. Severity alone does not decide what blocks the exit verdict of the run. Phase 4 records `blocking: true|false` on every finding from its own merit judgment, and `stop-clean` in Phase 8 of `SKILL.md` reads that flag:

- `blocking: true`: the finding must be resolved before merge. This is any Blocker, Critical, or High by default, **plus** any Medium, Low, or Nit that Phase 4 raised. Phase 4 raises a finding that brings back a variant of the bug under repair. It also raises a finding that leaves the regression of the fix without test coverage. Last, it raises a finding that the Conclusion of the reviewer put under "Must fix before merge".
- `blocking: false`: recorded, with no further action. This includes a Blocker, Critical, or High that the user and the session explicitly agreed to defer. The report still lists the deferral.

An unresolved `blocking: true` finding forces `stop-max-rounds`, at any severity label. Phase 8 also reads the label of a Blocker, Critical, or High. So an unflagged one can never clear `stop-clean` by accident.

---

## Triage-presentation format (Phase 4)

After all reviewer output is in, and before any fix, print the `Round <N> findings` block of Phase 4 in `SKILL.md`. That template is the canonical one, including the `(<Y> blocking)` count of each severity. Wait for the acknowledgment of the user only with `--interactive`.

A row whose severity is in `--skip` shows `(deferred — --skip <token>)`. A row whose severity is not in `--skip` shows `(will fix)`. With `--skip none`, every row shows `(will fix)`, and no deferred note appears.

---

## `--skip` interaction matrix

| `--skip` value | Severities fixed now | Severities deferred |
|----------------|---------------------|---------------------|
| `none` _(default)_ | Blocker, Critical, High, Medium, Low, Nit | _(none)_ |
| `nit` | Blocker, Critical, High, Medium, Low | Nit |
| `low,nit` | Blocker, Critical, High, Medium | Low, Nit |
| `medium,low,nit` | Blocker, Critical, High | Medium, Low, Nit |
| `critical,high,medium,low,nit` | Blocker only | Critical, High, Medium, Low, Nit |
| `blocker` | Critical, High, Medium, Low, Nit | Blocker (deferred to a later cycle. Use this only to ship known-broken code on purpose.) |

Any subset of the six tokens is valid. Each token that the value leaves out can get a fix. Each token in the value is deferred. The rows above are examples, not the full set.

---

## Type taxonomy

One type for each finding. Use these exact tokens in every report table and in the output of every phase.

| Type | Definition |
|------|------------|
| `Bug` | Wrong behavior: wrong output, wrong state, or wrong control flow. |
| `Reliability` | Code that works today but fails under errors, load, or concurrency. Examples: missing retries, unbounded collections, unhandled exceptions. |
| `Security` | Injection, credential exposure, broken authentication or authorization, missing input validation, insecure defaults. |
| `Performance` | N+1 queries, needless allocations, missing pagination, synchronous blocking in async paths. |
| `Maintainability` | Code that is correct but harder to change than it needs to be. Examples: deep nesting, magic literals, duplicated logic, misleading names. |
| `Test` | Missing coverage of critical paths, assertions that do not test the contract, flaky setup. |
| `Style` | Formatting, naming conventions, whitespace, with no semantic impact. |
| `Architecture` | Structural issues across components: DI lifetime mismatches, layer violations, wrong abstractions, broken contracts between components. |
| `Spec` | A finding in a target that is not code: a spec, a design doc, or a change of the spec framework (for example, OpenSpec). |
| `Docs` | Missing, wrong, or misleading documentation, comments, or changelog entries. |
