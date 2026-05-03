---
description: Iterative multi-agent review loop - review all branch changes, fix issues, re-review until clean. Use after completing implementation work when you want thorough quality verification before merging.
---

Run an iterative code review cycle that uses a multi-agent team to find issues, fixes them, and re-reviews until the branch is clean.

**Arguments**: $ARGUMENTS

- Format: `[scope] [options]`
- `scope` — what to review (optional, default: all changes on the branch vs base)
  - `all` or empty — full branch diff against base
  - `phases 5-13` — conceptual scope hint for the reviewers
  - `last 3 commits` — only recent commits
- Options:
  - `--skip <severities>` — comma-separated severities to skip (default: `medium,low`). Values: `critical`, `high`, `medium`, `low`. Example: `--skip low` fixes everything except low; `--skip medium,low` (default) fixes only blockers/critical/high
  - `--max-rounds N` — cap review iterations (default: 3)
  - `--base <branch>` — base branch to diff against (default: auto-detect from git)

## Why this exists

A single reviewer misses things. Different perspectives (architecture, security, testing, domain logic) catch different classes of bugs. Running multiple review passes catches issues introduced by fixes themselves. This command automates that cycle so you don't have to orchestrate it manually.

## Steps

### 1. Determine the diff scope

Identify the base branch and compute the full diff:

```bash
git log --oneline <base>..HEAD        # commits to review
git diff <base>...HEAD --stat         # files changed
```

If `--base` not provided, use the main/master branch or the branch configured in the repo. If scope is "last N commits", use `HEAD~N` instead of the base branch.

### 2. Round 1 — Full review via audit-team

Launch the `/audit-team` command targeting the changed files. The audit-team provides multi-perspective coverage (architecture, QA, security, domain, devil's advocate).

Frame the review prompt to focus on:

- **Bugs and logic errors** — incorrect mappings, missing null checks, data loss
- **Security** — injection, credential exposure, broken auth
- **Data integrity** — broken FK relationships, silent data truncation, lost updates
- **Performance** — N+1 queries, unbounded collections, missing pagination
- **DI lifetime** — scoped vs singleton mismatches, captive dependencies
- **Contract breaks** — REST API shape changes, interface violations
- **Test coverage** — untested critical paths, assertions that don't actually verify anything

The audit-team should review the actual changed code (read the files), not just the diff. Context matters — a change that looks fine in isolation might break something elsewhere.

### 3. Triage the report

From the consolidated audit-team report, categorize findings:

| Action       | Severity          | Criteria                                             |
|--------------|-------------------|------------------------------------------------------|
| **Fix now**  | Blocker, Critical | Data loss, security holes, broken contracts, crashes |
| **Fix now**  | High              | Logic errors, missing error handling, N+1 patterns   |
| **Defer***   | Medium            | Code quality, minor pattern violations, cleanup      |
| **Defer***   | Low               | Style, naming, minor improvements, "nice to have"    |

*Skipped by default. Override with `--skip low` to fix medium, or `--skip none` to fix everything.

Defer any severity listed in `--skip` (default: medium and low are deferred).

Present the triage to the user before fixing:

```text
Round 1 findings:
  Critical: 1 (will fix)
  High: 3 (will fix)
  Medium: 2 (will fix — small changes)
  Low: 4 (deferred)
  
Proceeding to fix 6 issues...
```

### 4. Fix issues

For each issue to fix:

1. Read the affected file to understand context
2. Make the minimal correct fix — don't refactor surrounding code
3. If the fix touches tests, run those tests to verify
4. Track what was changed

After all fixes, run a build to verify nothing broke:

```bash
dotnet build <solution> --no-restore
```

If tests are affected, run them too.

### 5. Commit the fixes

Stage only the files that were changed by fixes (not unrelated uncommitted changes):

```bash
git add <specific-files>
git commit -m "Review round N: Fix <summary of issues fixed>"
```

**Never push.** The user decides when to push.

### 6. Round N+1 — Re-review fix scope

If there are remaining rounds (`--max-rounds`), re-review but ONLY the files changed in the fix commit. Launch a smaller audit-team (3 agents is sufficient for re-review) focused on:

- Did the fix actually resolve the issue?
- Did the fix introduce new problems?
- Are there any regressions?

If this round finds new blockers/critical/high issues, fix them and loop again. If clean (or max rounds reached), stop.

### 7. Final summary

Present a summary of the entire review loop:

```text
## Review Loop Complete

Rounds: 2 of 3 max
Build: passing (0 errors, 0 warnings)
Tests: 5,892 passed, 0 failed

### Round 1 (full review)
- Found: 1 critical, 3 high, 2 medium, 4 low
- Fixed: 1 critical, 3 high, 2 medium
- Deferred: 4 low

### Round 2 (re-review of fixes)
- Found: 0 issues
- Status: clean

### Deferred items
- [Low] L1: description...
- [Low] L2: description...
```

## Guardrails

- **Never push** — commits stay local. The user pushes when ready.
- **Never touch unrelated files** — only fix what the review identified.
- **Verify fixes** — build after every fix round. Run affected tests.
- **Be honest about uncertainty** — if a finding is ambiguous, flag it for the user rather than silently ignoring or blindly fixing.
- **Respect --max-rounds** — don't loop forever. If issues persist after max rounds, report them as unresolved.
- **Don't over-fix** — a review loop is not a refactoring session. Fix the identified issues, nothing more.
