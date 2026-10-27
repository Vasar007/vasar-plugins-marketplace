# Review Loop Output Formats

Phase 9 and the "Run format" section of `SKILL.md` use this file.

## Phase 9 summary template

```text
## Review Loop Complete

Rounds: <N> of <max> max
Build: <passing (0 errors, 0 warnings) | failing (<details>) | skipped (no command resolved)>
Tests: <X passed, Y failed, Z skipped | not run>
Stop verdict: <stop-clean | stop-max-rounds | stop-blocked>
Fixed files: <path of each fixed file | none>

### Round 1 (<target-summary>)
  Found:    <B> Blocker, <C> Critical, <H> High, <M> Medium, <L> Low, <N> Nit
  Fixed:    <count> (APPLY=<A>, PARTIAL=<P>, REJECT=<R>)
  Deferred: <count> (per --skip / merit triage)

### Round 2 (re-review of fix diff, or of the whole target with `--no-commit`)
  Found: <count> issues
  Status: <clean | new issues>

...

### Deferred items (by severity; (blocking) = Phase 4 marked it must-fix-before-merge)
  [High]   H1: <short description> (blocking)
  [Medium] M1: <short description> (blocking)
  [Low]    L1: <short description>
  ...

### Rejected findings
  <#> REJECT: <reason>
  ...

### Decisions for your review (only with `--autonomous`)
  <#> <finding>: <decision and reason>
  ...
```

## Output formats

### Brief format (printed to chat after every cycle)

Print it at the end of every cycle. If the run format applies (see "Run format"), write it into the cycle report, and print only one status line. A run with more than one cycle collects these into the final summary of Phase 9.

```text
Cycle <N> — <target-summary>
  <count> findings: <Blk> Blocker, <Cri> Critical, <Hi> High, <Me> Medium, <Lo> Low, <Ni> Nit
  Triage: fix=<F>, deferred=<D> (per --skip / merit triage)
  Fix verdicts: APPLY=<A>, PARTIAL=<P>, REJECT=<R>
  Build: <pass|fail|skipped (no command resolved)>
  Tests: <X passed, Y failed, Z skipped | not run>
  Verdict: <continue|stop-clean|stop-max-rounds|stop-blocked>
```

### Full format

The Full format of the reviewer report is in `references/reviewer-briefs.md`, because the reviewer gets it with the Common Rules. Phase 3 reads that file in every run. Each cycle report uses the same format, and goes to chat or to `<target-slug>-cycle-<N>.md` in the reviews folder as the "Report destination rules" say.
