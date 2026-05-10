---
name: review-loop
description: "Iterative multi-agent review loop for anything reviewable — branch diffs, PR diffs, spec files, individual classes or methods, or arbitrary file targets. Each cycle dispatches a reviewer (or parallel reviewer pair), triages findings by severity, runs a verify-then-fix subagent that classifies every finding as APPLY/PARTIAL/REJECT before touching code, then re-reviews only the fix diff until clean or max rounds reached. Triggers on requests like 'run a review loop', 'review the PR', 'review this branch', 'review these changes', 'do a code review', '/review-loop', '/review-pr', 'review this file', 'review the spec', 'full review pass', 'iterative review', 'multi-agent review'."
---

# Review Loop

A single reviewer misses things. Different perspectives — architecture, security, testing, domain logic — catch different classes of bugs. Running multiple review passes catches issues introduced by fixes themselves. This skill automates that cycle: each round dispatches one or more reviewers in parallel, triages findings, runs a dedicated verify-then-fix agent that rejects unverified theories, and re-reviews only the fix diff. The result is a review record with explicit APPLY/PARTIAL/REJECT verdicts rather than a pile of speculative suggestions.

## When to use

- Reviewing a feature branch before merge (`target=branch`, the default).
- Reviewing a full PR diff by ID (`target=pr <id>`).
- Reviewing only the last N commits (`target=commits <N>`).
- Reviewing a spec, OpenSpec change, or design doc (`target=spec <path>`).
- Reviewing any file not in a diff (`target=file <path>`).
- Reviewing a specific C# class or method (`target=class <FQN>` / `target=method <FQN>`).
- Legacy phrases: `/review-loop`, `/review-pr`, "run a review loop", "review the PR".

## When NOT to use

- Acting on pull-request review comments posted by human reviewers — use `dev-essentials:process-pr-comments`.
- Composing or updating a PR description — use the PR Composer agent.
- A single one-off review with no iterative loop (just invoke `dev-essentials:process-pr-comments` or ask Claude to review the diff inline).

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| `target=` | `branch` | What to review. Values: `branch`, `pr <id>`, `commits <N>`, `diff <range>`, `file <path>`, `class <FQN>`, `method <FQN>`, `spec <path>`. |
| `--base <branch>` | auto-detect from git | Base branch for `branch` / `pr` targets. |
| `--rounds <N>` | `3` | Maximum review-fix-re-review cycles. |
| `--skip <severities>` | `medium,low,nit` | Comma-separated severity tokens to defer rather than fix. Valid tokens: `blocker`, `critical`, `high`, `medium`, `low`, `nit`. Each token is independent — `--skip medium,low` defers Medium and Low but NOT Nit. Use `--skip none` to fix every severity. |
| `--reviewer <id>` | `audit-team` | Reviewer subagent(s). Values: `audit-team`, `dual`, `feature-dev:code-reviewer`, `pair <a>+<b>`, `quad <a>,<b>,<c>,<d>`, or any `<plugin>:<agent>`. |
| `--reviewer-model <model>` | inherit | Model tier override for the reviewer subagent (e.g. `opus`, `sonnet`, `haiku`). Passed via the `model:` field of each reviewer Agent dispatch. |
| `--reviewer-focus <tokens>` | (brief default) | Comma-separated focus-area tokens that override the default focus list in the reviewer brief (e.g. `security,performance,test-coverage`). Valid tokens are defined in `references/reviewer-briefs.md` (Phase 3 loads that file unconditionally; the canonical token list lives there). If every token is unrecognized, falls back to the brief's default list with a warning. If only some tokens are unrecognized, uses the recognized tokens and warns about the unrecognized ones. |
| `--fixer <id>` | `general-purpose` | Verify+fix subagent. Same value space as `--reviewer`. |
| `--fixer-model <model>` | inherit | Model tier override for the fixer subagent. Passed via the `model:` field of the fixer Agent dispatch. |
| `--audit-team-args <...>` | none | Free-form pass-through to the `/audit-team` command when `--reviewer audit-team`. Ignored (with a warning) when `--reviewer` is not `audit-team`. |
| `--no-verify-fix` | off | Skip Phase 5 fix edits. Phase 6 still runs against existing code as a sanity check. Phase 7 is skipped. Phase 9 still runs. |
| `--dry-run` | off | Skip Phase 5 fix edits, skip Phase 6 (nothing changed, so no build/test to run), skip Phase 7. Phase 9 still runs. |
| `--auto-proceed` | off | When off (default), wait for explicit user acknowledgment of the Phase 4 triage before starting Phase 5. When on, proceed without waiting. |
| `--save-reports` | off | Force-save every full cycle report to `Notes/Reviews/` even on single-cycle runs. |
| `--print-reports` | off | Force-print every full cycle report to chat even on multi-cycle runs. |
| `--include-resolved` | off | Only meaningful when `target=pr <id>`. Active and pending threads are always fetched and always appear in the reviewer brief as an **"Open reviewer threads"** section (regardless of this flag). When `--include-resolved` is set: (1) the Phase 1 PR-thread fetch also includes resolved/closed threads; and (2) the Phase 3 reviewer brief gains an additional **"Previously addressed in this PR"** section listing each resolved/closed thread so the reviewer can avoid re-raising already-handled issues. Has no effect on non-PR targets. |

Every flag and `target=` value has an explicit default above. No parameter is optional-but-undefined.

## Flag interaction matrix

The three control flags affect phases independently. Consult this matrix before executing each phase:

| Flag | Phase 5 (fix edits) | Phase 6 (build/test) | Phase 7 (commit) | Phase 8 (loop) | Phase 9 (summary) |
|---|---|---|---|---|---|
| _(none)_ | runs | runs | commits | continues if eligible | runs |
| `--dry-run` | **skipped** | **skipped** (nothing changed) | **skipped** | **stops** (no edits to re-review) | runs |
| `--no-verify-fix` | **skipped** | runs against existing code | **skipped** | **stops** (no edits to re-review) | runs |

Rules:
- `--dry-run` and `--no-verify-fix` are mutually exclusive: if both are set, **STOP and ask the user which behavior is intended** before proceeding.
- `--auto-proceed` is independent of both flags above.

## Report destination rules

Single-cycle runs default to printing the full cycle report to chat. Multi-cycle runs default to writing each cycle report to `Notes/Reviews/<target-slug>-cycle-<N>.md` to avoid replaying long reports in the chat context.

- `--save-reports`: forces write-to-file even for single-cycle runs.
- `--print-reports`: forces print-to-chat even for multi-cycle runs.
- Phase 9 (final summary) follows the same destination rule: write-to-file when multi-cycle or `--save-reports`; print-to-chat otherwise. File path: `Notes/Reviews/<target-slug>-summary.md`.

## Severity and type taxonomy

Every finding carries one severity and one type. Use these values consistently across all output formats and phases — do not invent new levels or abbreviate.

| Severity | When to use |
|---|---|
| Blocker | Will not merge / will not ship — data loss, security holes, broken contracts, crashes. |
| Critical | Must fix before merge — logic errors with significant impact, missing critical error handling. |
| High | Should fix before merge — N+1 patterns, unsound assumptions, weak coverage of critical paths. |
| Medium | Quality issue — pattern violations, minor coverage gaps, cleanup opportunities. |
| Low | Nice-to-have — minor improvements, refactoring opportunities. |
| Nit | Style only — naming, formatting, conventions. |

**Type categories** (one per finding): `Bug`, `Reliability`, `Security`, `Performance`, `Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`. Use `Spec` and `Docs` for non-code targets; they are additive to the set from `review-pr`.

The taxonomy matters because it drives the triage decision in Phase 4 and the deferred-items list in Phase 9. If you use an unlisted severity or type, downstream triage logic becomes undefined.

## Phases (the workflow)

### Phase 1 — Resolve target

Convert `target=` into a concrete diff or file set. The following resolution is exact — no "best effort" guessing:

| `target=` | Resolution |
|---|---|
| `branch` | Auto-detect `<base>` from git if `--base` not set: (1) run `git symbolic-ref refs/remotes/origin/HEAD` and strip the `refs/remotes/origin/` prefix to get the bare branch name — this returns the remote's actual default (e.g. `main`, `master`, or `release/1.0/master`); (2) if that command fails or returns nothing, check `git rev-parse --verify origin/main` then `git rev-parse --verify origin/master` and use the first that succeeds; (3) if none succeeds, **STOP and ask the user for the base branch**. A user-supplied `--base <branch>` always wins over auto-detect (top priority). After resolving `<base>`, run `git fetch origin <base>` to refresh the remote-tracking ref. If the fetch fails (network unavailable, remote not configured, etc.), **STOP and ask the user** — do NOT silently fall back to a stale local `<base>` ref. Then diff using the remote-tracking name: `git diff origin/<base>...HEAD`. Never diff against a local `<base>` ref, which may be absent or stale. |
| `pr <id>` | Full branch diff for the named PR via GitHub MCP (see `dev-essentials:github-mcp-conventions` for how to call `pull_request_read` with explicit `owner` and `repo`). If the MCP call fails (MCP unavailable, PR not found, auth missing), **STOP and ask the user** — do NOT silently fall back to a local diff. After reading PR metadata, derive source and target branch names, then run `git fetch origin <sourceBranch> <targetBranch>`. Then diff using remote-tracking names: `git diff origin/<targetBranch>...origin/<sourceBranch>` — never rely on local branch names, which may be absent or stale. **Thread fetch (runs in parallel with the diff resolution above — both are independent operations):** call `pull_request_read` to retrieve review comments with pagination; paginate with bounded `per_page` until exhausted (see `dev-essentials:github-mcp-conventions` Rule 3). Status filter: by default keep only active/unresolved threads; when `--include-resolved` is set, also include resolved threads. The collected threads are passed forward to Phase 3. |
| `commits <N>` or `last-N` | `git diff HEAD~N..HEAD`. |
| `diff <range>` | `git diff <range>` verbatim. |
| `file <path>` | Read the file at `<path>` in full. |
| `spec <path>` | Read the file at `<path>` in full; brief the reviewer for spec-style review. |
| `class <FQN>` | Locate the class via `grep -rn "class <SimpleName>"` under the repo root. If exactly one match: extract that file and line range. If zero or multiple matches: **STOP and ask the user** — "Which file and line range contains `<FQN>`?" — before proceeding. Never pick a candidate silently. |
| `method <FQN>` | Resolve the containing type first (same file-location logic as `class <FQN>` — `grep -rn "class <ContainingType>"` under the repo root; if zero or multiple files match, **STOP and ask the user** which file to use). Within that file, search for the method name: scan for `\b<MethodName>\b` followed by `(` on the same line OR within ≤2 lines (handles long parameter lists). If **exactly one** match is found, extract the line range from the method declaration to its closing brace (use brace counting or read until the next method/end-of-class). If **zero or multiple** matches are found (overloads), **STOP and ask the user**: "Found `<N>` matches for method `<MethodName>` in `<file>`. Which line range should I review?" — do NOT pick silently. |

Free-form scope hints (e.g. "phases 5-13", "cleanup module") are passed as a context hint in the reviewer brief and echoed back in the cycle's brief output as "scope hint: `<text>`" so the user can confirm it was received.

### Phase 2 — Resolve reviewer + fixer

Validate `--reviewer` and `--fixer` against the installed plugin set before dispatching. Use these rules exactly:

- If the value is `audit-team`: invoke the `/audit-team` command pattern with `--audit-team-args` appended if provided.
- If the value is a `<plugin>:<agent>` form: verify the plugin is installed. Check whether the plugin appears in the session's known skill list. If it does not appear, **fall back to `dual` and print a warning**: "Reviewer `<id>` not found — falling back to `dual` (feature-dev:code-reviewer + general-purpose). Install the plugin and retry if you want the specified reviewer." Pre-dispatch agent-name validation is not possible (Claude Code's agent surface is opaque until dispatch), so additionally: **if the plugin is installed but agent dispatch fails at runtime** (e.g. the agent name is misspelled or the agent no longer exists in the installed plugin version), treat the ID as unresolvable, apply the same fallback (`dual` for `--reviewer`, `general-purpose` for `--fixer`), and print a warning naming the failed dispatch — for example "Agent `<id>` dispatch failed — falling back to `<fallback>`. Verify the agent name against the installed plugin."
- If the value is `dual`: use `feature-dev:code-reviewer` + `general-purpose` in parallel. If `feature-dev` is not installed, fall back to `general-purpose` × 2 with two distinct briefs, with a warning naming the fallback. If `general-purpose` is also unavailable, **STOP and ask the user to install at least one reviewer plugin** — do NOT proceed with an empty reviewer set.
- If the value is `pair <a>+<b>` or `quad <a>,<b>,<c>,<d>`: validate each ID individually. When a slot is unresolvable, replace ONLY that slot with `general-purpose` and print a warning naming the unresolved slot (e.g. "Slot `<id>` not found — substituted `general-purpose`"). Do NOT collapse the full pair/quad to `dual`.
- The **same fallback rule applies to `--fixer`**. An unresolvable fixer ID falls back to `general-purpose` with a warning.
- When `--reviewer` is not `audit-team`, `--audit-team-args` is ignored. Print a warning: "`--audit-team-args` is set but `--reviewer` is `<value>`, not `audit-team` — ignoring `--audit-team-args`."

The fallback rule is uniform — it applies to any unknown agent ID, not only `feature-dev:code-reviewer`. The user is always told which ID was unresolvable and what was substituted.

### Phase 3 — Round-N review

Before composing the reviewer brief or validating `--reviewer-focus` tokens, load `references/reviewer-briefs.md` to obtain the per-target brief template AND the canonical `--reviewer-focus` token list. Use the loaded list to validate user-supplied tokens (recognized tokens override the default focus list; unrecognized-only tokens fall back with a warning).

Dispatch the reviewer per the rules in `dev-essentials:subagent-orchestration`. Do not restate those rules here — cross-reference them. Key dispatch decisions:

- **Foreground-parallel** when more than one reviewer is selected (multiple Agent calls in one assistant message, no `run_in_background`).
- **Foreground** for a single reviewer.
- **Background-parallel** only when every prerequisite listed in `subagent-orchestration` Rule 3 holds simultaneously.

Pass `--reviewer-model` to each reviewer subagent's Agent dispatch via the `model:` field when the flag is set.

Brief the reviewer with:

- Target diff or file contents (do not ask the reviewer to re-fetch what has already been resolved in Phase 1).
- Focus areas: bugs and logic errors, security (injection, credential exposure, broken auth), data integrity (FK breaks, silent truncation, lost updates), performance (N+1, unbounded collections), DI lifetime mismatches, contract breaks, test coverage of critical paths.
- Read the actual changed code — not just the diff. Context matters; cross-file consequences are invisible in isolation.
- For `branch` / `pr` / `commits` targets: verify changes are coherent across commits (no regressions introduced in earlier commits that a later commit masks).
- Call out missing tests or inadequate coverage explicitly.
- If something cannot be determined from the provided material, ask a specific question rather than guessing. Flag it as a question in the findings.
- Attribute the review model: every reviewer's report ends with "Review made by `<MODEL>`".
- **Round number is set by this skill** — always "Round N" where N is the current cycle count tracked by this skill. The reviewer must NOT look in the conversation history to infer a round number.

**`target=pr <id>` — open threads (always):** when `target=pr <id>`, always insert an **"Open reviewer threads"** section into the reviewer brief, populated from the active/unresolved threads fetched in Phase 1. Place this section BEFORE the "Previously addressed in this PR" section (when present). Format:

```
### Open reviewer threads
(Existing questions or issues raised by reviewers — not findings you wrote. They may indicate hot
spots worth looking at more closely, or findings you can independently endorse or refute. Do NOT
re-attribute these as your own findings.)

- [T#<threadId>] <Severity> <Type> on <file>:<firstLine> — <one-line summary> — status <Active|Pending>
- ...
```

If there are no active/pending threads, omit this section entirely. This section is inserted regardless of whether `--include-resolved` is set.

**`target=pr <id>` with `--include-resolved`:** when both conditions hold, append a "Previously addressed in this PR" section to the reviewer brief. List every resolved/closed thread in this format:

```
### Previously addressed in this PR
(For context only — do not re-raise these unless the surrounding code regressed.)

- [T#<threadId>] <Severity> <Type> on <file>:<firstLine> — <one-line summary> — resolved as <statusLabel>
- ...
```

If there are no resolved/closed threads, omit this section entirely.

Full reviewer brief templates per target type live in `references/reviewer-briefs.md`. Read that file when composing the reviewer subagent's prompt.

### Phase 4 — Triage

After collecting all reviewer output, produce a triage table before taking any action:

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

Apply `--skip` exactly: each severity token in `--skip` is its own independent gate — `--skip medium,low` defers Medium and Low but Nit remains eligible for fixing. When `--skip none`, every severity row shows "(will fix)" and no "(deferred)" rows appear. Print the triage and **wait for the user to acknowledge** before starting Phase 5, unless `--auto-proceed` is set — in that case proceed immediately.

For triage reference and the full severity-to-action mapping see `references/triage-matrix.md`.

### Phase 5 — Verify-then-fix

**Skipped when `--dry-run` or `--no-verify-fix` is set** (see flag interaction matrix above).

Dispatch the fixer subagent. Pass `--fixer-model` to the fixer Agent dispatch via the `model:` field when the flag is set. The fixer's job is to filter unverified theories OUT of the fix pass — the verify-before-apply discipline is the core value of this skill over a naive fix loop. Detailed playbook in `references/verify-fix-discipline.md`. Inline rules the fixer MUST follow:

- For each finding: classify as **APPLY**, **PARTIAL**, or **REJECT** before touching any file.
  - APPLY: the finding is verified against a primary source (official docs, known-working example, the repo's own working code, CLAUDE.md, or a throwaway test). Apply the fix as described.
  - PARTIAL: the finding is partially correct but the proposed fix needs adjustment. Apply the verified portion; note what was adjusted.
  - REJECT: the finding is unverified, ambiguous, or based on pattern-matching without a primary source. Do NOT apply it. Report the rejection reason.
- **Never touch unrelated files.** Only edit files named in the triage, plus directly related supporting files that are structurally required (see `references/verify-fix-discipline.md` §6 — covers e.g. the matching `*Tests.cs` for a missing-test-coverage finding, or the config registration file for a missing-config-knob finding). The strict no-drift default still applies — do not extend into unrelated refactors.
- **Don't over-fix.** Fix the identified issue; do not refactor surrounding code or fix adjacent issues not on the triage list.
- **Be honest about uncertainty.** Flag ambiguous findings as PARTIAL/REJECT with reasons. Do not silently skip or blindly apply.
- After every fix, confirm the edit matches the reviewer's intent. If intent is ambiguous, ask rather than guessing.
- Report the classification for every finding, including REJECTs. No silent discards.

Cross-reference `dev-essentials:engineering-discipline` Rule 2 — no unilateral critical decisions (public signature changes, new DI dependencies, test assertion relaxations) that the triage does not authorize.

### Phase 6 — Build / test verify

**Skipped when `--dry-run` is set** (nothing was changed, so there is nothing to verify). When `--no-verify-fix` is set, Phase 6 runs against the existing code as a sanity check.

After the fixer completes (or, for `--no-verify-fix`, against existing code), run the repo's build and test suite. Build/test verification is **mandatory in all other cases** — there is no flag to skip it. Rationale: `dev-essentials:engineering-discipline` Rule 1 (own every red signal in your session). Any failure that the fix pass introduces is this skill's failure, not a pre-existing issue.

**Non-code targets:** When `target=spec`, OR when `target=file <path>` and the file extension is a documentation format (`.md`, `.txt`, `.rst`, `.adoc`), AND no validator (e.g., `openspec validate`, a doc linter) is documented in CLAUDE.md: **skip Phase 6** with a single-line note in the cycle's brief: `Phase 6 skipped — non-code target with no validator`. If a validator IS documented in CLAUDE.md (e.g., `openspec validate`), Phase 6 runs that validator instead of a build/test command.

**Code-oriented targets with no auto-detectable build command:** `target=class <FQN>`, `target=method <FQN>`, and `target=file <path>` with a non-documentation extension always point at code. Do **not** skip Phase 6 for these — instead follow command resolution step 3 below and ask the user: "What is the build command for this repo?" Then record the answer and run Phase 6 normally. The mandatory-verification contract above admits no exception for code targets.

Command resolution order — follow this exactly:

1. Read the repo's `CLAUDE.md`. If it documents a build command or test command, use that.
2. If CLAUDE.md is silent: auto-detect from repo contents. For every manifest type below, apply
   the same three-way rule: **exactly one** → use it; **zero** → skip to the next type;
   **two or more** → **STOP and ask the user** with the file list before proceeding.
   - `*.sln` (C# / .NET) — count matching files:
     - **Exactly one** `.sln`: use it for `dotnet build <solution>` / `dotnet test <solution>`.
     - **Zero** `.sln`: skip this branch and continue to the next auto-detect step.
     - **Two or more** `.sln`: **STOP and ask the user** — "Multiple solutions found: `<list>`. Which solution should Phase 6 build and test?" — record the answer and use it for both commands.
   **Other ecosystems (Node, Rust, Python, Go, etc.):** auto-detect is not implemented for non-.NET stacks. Apply the same single-manifest resolution logic as `.sln` if a clear analogue exists for the language at hand (`package.json`, `Cargo.toml`, `pyproject.toml`/`setup.py`, `go.mod`, etc.) — exactly one → use it; zero → skip; two or more → STOP and ask. Whichever manifest is selected, run the build/test commands from that manifest's directory (cd into it, or use the equivalent `--prefix` / `--manifest-path` / `-C` flag), not from the repo root. **If the language detection or the directory-bound command form is unclear, STOP and ask the user for the build and test commands** rather than guessing — do not silently fall back to a repo-root invocation.
3. If auto-detection produces no match: **STOP and ask the user** — "What is the build command for this repo?" — then record the answer and proceed.

If the build or tests fail:
- Report the failures honestly. Do not claim "pre-existing".
- If the failure is in code touched by the fix pass, treat it as a regression: return to Phase 5 for that finding and attempt one re-fix.
- If Phase 5 cannot resolve the regression after one re-attempt (the fixer reports REJECT or PARTIAL and cannot produce a passing build), exit the loop with `stop-blocked`, include the regression in Phase 9's deferred-items list, and report to the user.

### Phase 7 — Commit fixes

**Skipped when `--dry-run` or `--no-verify-fix` is set** (see flag interaction matrix above).

Stage and commit only the files changed in this fix pass. Never `git add -A` or `git add .`.

Commit message format:

```text
Review round <N>: Fix <short summary of issues fixed>

<optional 1-3 lines explaining the most significant fix>
```

Rules:
- One commit per round by default.
- **Never push by default.** The user pushes when ready. The user can explicitly grant permission to push (e.g. "you can push after each fix commit").

### Phase 8 — Repeat or stop

Decide whether to run another cycle. The decision is deterministic:

- **Continue** if ALL of the following hold: (a) rounds used < `--rounds`, AND (b) the fixer applied at least one edit in this cycle (new code is on disk).
  - If no edit was applied in this cycle (all findings were REJECT or the cycle was `--dry-run`/`--no-verify-fix`), **stop** — there is no new code to re-review.
  - When the fixer applied zero edits in the re-review cycle, **skip Phase 6** for the next round — there is no new code to verify; carry forward the previous cycle's build/test status into Phase 9.
  - The re-review scope is ONLY the files changed in the fix commit, not the full original target. This is intentional: re-reviewing the whole target conflates new findings with old deferred ones.
  - The re-review in Round N+1 always uses a single `general-purpose` agent regardless of `--reviewer`. The full reviewer/fixer config applies only to Round 1. The goal is "did the fix resolve the issue and introduce no regressions?" — not a full architectural review.
- **Stop** otherwise. Classify the stop verdict:
  - **stop-clean**: BOTH of the following hold: (1) no Blocker/Critical/High findings remain within the re-review scope, AND (2) no Blocker/Critical/High findings appear in the deferred-items list across the entire run (whether deferred via `--skip` or marked PARTIAL/REJECT-then-deferred by the fixer). If either condition fails, classify as `stop-max-rounds` instead.
  - **stop-max-rounds**: `--rounds` limit reached before a re-review pass could confirm clean — covers all four cases that prevent a `stop-clean` classification: (a) issues remain open in the re-review scope; (b) every finding was deferred via `--skip`; (c) every finding was fixed but no re-review round ran to confirm; (d) one or more Blocker/Critical/High findings were deferred (via `--skip critical`, `--skip high`, etc.) so merge-blocking work is still outstanding even though the rounds limit was not reached. The user sees `stop-max-rounds` instead of a misleading `stop-clean` whenever merge-blocking severity findings remain unresolved anywhere in the run.
  - **stop-blocked**: the build or tests are failing and cannot be resolved in this session; escalate to user.

### Phase 9 — Final summary

Aggregate across all cycles. Follow the report destination rules (see "Report destination rules" section above): write to `Notes/Reviews/<target-slug>-summary.md` when multi-cycle or `--save-reports`; print to chat otherwise.

Format:

```text
## Review Loop Complete

Rounds: <N> of <max> max
Build: <passing (0 errors, 0 warnings) | failing (<details>) | skipped (no command resolved)>
Tests: <X passed, Y failed, Z skipped | not run>
Stop verdict: <stop-clean | stop-max-rounds | stop-blocked>

### Round 1 (<target-summary>)
  Found:    <B> Blocker, <C> Critical, <H> High, <M> Medium, <L> Low, <N> Nit
  Fixed:    <count> (APPLY=<A>, PARTIAL=<P>, REJECT=<R>)
  Deferred: <count> (per --skip)

### Round 2 (re-review of fix diff)
  Found: <count> issues
  Status: <clean | new issues>

...

### Deferred items (by severity)
  [High]   H1: <short description>
  [Medium] M1: <short description>
  ...

### Rejected findings
  <#> REJECT: <reason>
  ...
```

---

## Output formats

### Brief format (printed to chat after every cycle)

Print unconditionally at the end of every cycle. Multi-cycle runs accumulate these into the final summary table in Phase 9.

```text
Cycle <N> — <target-summary>
  <count> findings: <Blk> Blocker, <Cri> Critical, <Hi> High, <Me> Medium, <Lo> Low, <Ni> Nit
  Triage: fix=<F>, deferred=<D> (per --skip)
  Fix verdicts: APPLY=<A>, PARTIAL=<P>, REJECT=<R>
  Build: <pass|fail|skipped (no command resolved)>
  Tests: <X passed, Y failed, Z skipped | not run>
  Verdict: <continue|stop-clean|stop-max-rounds|stop-blocked>
```

### Full format (written per cycle to chat or to `Notes/Reviews/<target-slug>-cycle-<N>.md`)

Follow the report destination rules (see "Report destination rules" section above).

```markdown
# Review by AI Agent (Round-<N>) — <target-summary>

## Description

<100-200-character impression of the target.>

## Summary table

| # | Severity | Type | File:Line(s) | What's wrong | Suggested direction |
|---|----------|------|--------------|--------------|---------------------|
| 1 | Blocker | Security | <file>:<line> | <one short sentence> | <not the exact fix; "refactor", "add validation", "ok to accept risk", etc.> |
| ... | ... | ... | ... | ... | ... |

(Only meaningful items. Skip trivial commentary.)

## Details per item

For each row from the table:

### <#> <one-line header matching the table>

- **Problem:** 1–2 sentences.
- **Impact:** 1 sentence.
- **Recommendation:** 1–2 sentences (still no full code dumps).
- **Verification source** (when proposing a concrete fix): the primary source consulted (official
  docs / known-working example / throwaway test) per `dev-essentials:engineering-discipline`.
  If unverified, frame as a theory ("this might be …"), not a fix.

## Conclusion

In bullets:

- **Must fix before merge** — list of `#` numbers
- **Acceptable risks** — list of `#` numbers
- **Needs discussion** — list of `#` numbers

## Final verdict

One line:

- ✅ **Approve**
- ✅➕ **Approve with suggestions**
- 🕒 **Wait for author**
- ❌ **Reject**

## Reviewer model

Review made by `<MODEL>` (one line per reviewer if multiple ran in parallel — the skill
aggregates them in the cycle summary).
```

Both formats are inline in this SKILL.md (not in `references/`) so the AI composing the report has the templates loaded without a second tool roundtrip. Concrete filled-in samples live in `examples/` to make the formats tangible.

---

## Reviewer briefs

Reviewer brief templates per target type (branch, pr, commits, diff, file, class, method, spec) live in `references/reviewer-briefs.md`. Read that file when dispatching the reviewer subagent — it handles the per-target framing and the default focus-area list for each target type.

## Verify+fix discipline

The verify+fix subagent's job is to filter unverified theories out of the fix pass. The detailed playbook — primary-source verification steps, APPLY/PARTIAL/REJECT decision tree, common rejection patterns, escalation policy for ambiguous findings — lives in `references/verify-fix-discipline.md`. Read it before dispatching the fixer.

## Guardrails

- **Never push by default.** Commits stay local; the user pushes when ready. The user can explicitly grant permission to push (e.g. "you can push after each fix commit") — only then.
- **Never touch unrelated files.** Only edit files named in the current triage, plus structurally required supporting files (see `references/verify-fix-discipline.md` §6 — covers e.g. the matching `*Tests.cs` for a missing-test-coverage finding, or the config registration file for a missing-config-knob finding). Do not extend into unrelated refactors.
- **Verify before confident fixes.** Apply only APPLY/PARTIAL-classified findings. REJECT means no edit. See `dev-essentials:engineering-discipline`.
- **Be honest about uncertainty.** Flag ambiguous findings explicitly — as PARTIAL or REJECT with reasons — rather than silently ignoring or blindly applying them.
- **Don't over-fix.** Fix the identified issues only. This is not a refactoring session.
- **Respect `--rounds`.** Do not loop past the configured maximum. Report unresolved issues under "Deferred items" in the final summary.
- **Build/test verify is mandatory** unless `--dry-run` or `--no-verify-fix` is set. Any red signal after a fix round is owned by this skill session — investigate and fix, or escalate to the user.
- **Fall back to `general-purpose` on unknown or failed agent IDs.** Print a warning naming the unresolvable ID and the fallback applied. This applies to both `--reviewer` and `--fixer`, and covers two failure modes: (1) the plugin itself is not installed (caught during Phase 2 pre-dispatch validation); (2) the plugin is installed but the specific agent name is wrong or has been removed (caught when dispatch fails at runtime — apply the same fallback chain). If `general-purpose` is also unavailable, STOP and ask the user to install at least one reviewer plugin.
- **Never resolve round number from conversation history.** Round N is set by this skill's own cycle counter, starting at 1.

## Examples

| File | When to read |
|---|---|
| `examples/branch-review.md` | Feature branch review end-to-end — both report formats filled in with real numbers. |
| `examples/spec-review.md` | OpenSpec change document review — spec-focused reviewer brief and findings. |

## Cross-references

| Skill | Why this skill depends on it |
|---|---|
| `dev-essentials:engineering-discipline` | Rule 1 (own every red signal) drives Phase 6 build/test ownership. Rule 2 (no unilateral critical decisions) drives Phase 5 REJECT classification for signature changes the triage did not authorize. |
| `dev-essentials:subagent-orchestration` | Dispatch mode rules (foreground-parallel vs foreground vs background) for Phase 3 reviewer dispatch and Phase 5 fixer dispatch. |
| `dev-essentials:process-pr-comments` | Tone and reply-format parallel — that skill acts on human reviewer comments; this skill runs the AI review cycle. They are complementary, not redundant. |
| `dev-essentials:github-mcp-conventions` | When `target=pr <id>`, use this skill's rules for calling `pull_request_read` with explicit `owner` and `repo`. |
