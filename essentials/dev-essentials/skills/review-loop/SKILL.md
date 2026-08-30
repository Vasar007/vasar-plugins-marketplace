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
| `--skip <severities>` | `none` | Comma-separated severity tokens to defer **by label, unread**, rather than triage. Valid tokens: `blocker`, `critical`, `high`, `medium`, `low`, `nit`, and `none`. Each token is independent — `--skip medium,low` defers Medium and Low but NOT Nit. The default `none` defers nothing by label; every finding reaches Phase 4's merit-based triage instead (see Phase 4). Pass an explicit set (e.g. `--skip medium,low,nit`) only when label-based auto-deferral is genuinely what is wanted. |
| `--reviewer <id>` | `audit-team` | Reviewer subagent(s). Values: `audit-team`, `dual`, `feature-dev:code-reviewer`, `pair <a>+<b>`, `quad <a>,<b>,<c>,<d>`, or any `<plugin>:<agent>`. **`audit-team` is not an agent ID** — it is a slash command that takes a documentation `<path>`, so it is valid only for `target=spec <path>` and for `target=file <path>` whose extension is `.md`. On any other target it warns and falls back to `general-purpose` (Phase 2 has the full adapter). |
| `--reviewer-model <model>` | inherit | Model tier override for the reviewer subagent (e.g. `opus`, `sonnet`, `haiku`). Passed via the `model:` field of each reviewer Agent dispatch. |
| `--reviewer-focus <tokens>` | (brief default) | Comma-separated focus-area tokens that override the default focus list in the reviewer brief (e.g. `security,performance,test-coverage`). Valid tokens are defined in `references/reviewer-briefs.md` (Phase 3 loads that file unconditionally; the canonical token list lives there). If every token is unrecognized, falls back to the brief's default list with a warning. If only some tokens are unrecognized, uses the recognized tokens and warns about the unrecognized ones. |
| `--fixer <id>` | `general-purpose` | Verify+fix subagent. Same value space as `--reviewer`. |
| `--fixer-model <model>` | inherit | Model tier override for the fixer subagent. Passed via the `model:` field of the fixer Agent dispatch. |
| `--audit-team-args <...>` | none | Free-form pass-through to the `/audit-team` command when `--reviewer audit-team`, appended after the `<path>` positional Phase 2 supplies (Phase 2 also handles positional collisions — a user-supplied `[agent-count]` or `[model]` always wins over anything this skill would otherwise fill in). Ignored (with a warning) when `--reviewer` is not `audit-team`. |
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

- If the value is `audit-team`: `audit-team` is a **slash command, not an agent ID**, so it is not dispatched through the `Agent` `subagent_type` path the other values use, and it needs the adapter below. `/audit-team`'s own signature is `<path> [agent-count] [model] [mode]` — confirm against `commands/audit-team.md` before relying on defaults (`agent-count` default `5`; `model` default the current session's model; `mode` default `foreground`, values `foreground`/`background`).
  - **Target restriction.** Valid only when the Phase 1 target resolved to a documentation path: `target=spec <path>`, or `target=file <path>` whose extension is `.md` (`/audit-team` reads only `.md` files — narrower than Phase 6's non-code extension set, which also covers `.txt`/`.rst`/`.adoc`). Every other target — `branch`, `pr <id>`, `commits <N>`, `diff <range>`, `class <FQN>`, `method <FQN>`, or a non-`.md` `file` — resolves to a diff or a code symbol rather than a documentation path `/audit-team` can take, so **fall back to `general-purpose` and print a warning**: "`--reviewer audit-team` needs a documentation path target; `target=<value>` is not one — falling back to `general-purpose`."
  - **Argument mapping.** Invoke `/audit-team <path> [agent-count] [model] [mode]` with `<path>` = the Phase 1 resolved target path, then append anything left in `--audit-team-args` verbatim.
    - `[agent-count]` — from `--audit-team-args` if it names one, else `/audit-team`'s own default (`5`). Positionals cannot be skipped, so always fill this slot, including when the user supplied only a model: `--audit-team-args "opus"` must produce `/audit-team <path> 5 opus`, never `/audit-team <path> opus` (which `/audit-team` would read as `[agent-count]`).
    - `[model]` — the resolved `--reviewer-model`. Omit the positional (letting `/audit-team`'s own "current model" default stand) when `--reviewer-model` is `inherit` (this skill's own default) or unset, or when `--audit-team-args` already names a model.
    - `[mode]` — leave unset (its `foreground` default stands) unless `--audit-team-args` explicitly names `background`; this skill never requests `background` mode of its own accord. If a later positional is supplied, every slot before it must still be filled per the same no-skipping rule — e.g. naming `mode` without a `model` still requires filling the `model` slot first, even with a placeholder that reproduces the default.
  - **Output mapping — `/audit-team` returns 3 buckets, this skill triages 6 severities.** Map `Blockers` → **Blocker**, `Warnings` → **High**, `Suggestions` → **Low**. Record the originating bucket next to each mapped severity so Phase 4 can see it was not a native six-level grade, and re-grade an individual finding up or down when its own text plainly warrants it (a `Warning` describing a data-corrupting bug is Critical; a `Warning` about a non-normative "should" is Medium). `/audit-team` emits no **type** token: use `Spec` for `target=spec`, and for a documentation `target=file` derive the type from the finding's text per the type taxonomy, defaulting to `Docs`.
  - **Conclusion mapping.** `/audit-team`'s report has no "Must fix before merge / Acceptable risks / Needs discussion" section, which is what Phase 4 reads. Synthesize it: consolidated `Blockers` → Must fix before merge; `Warnings` → Needs discussion; `Suggestions` → Acceptable risks. Use `/audit-team`'s **agreement matrix** as the multi-role signal — a finding flagged by multiple roles is elevated. **Precedence:** multi-role agreement elevates a finding by one bucket (Suggestion → Warning, Warning → Blocker) but never skips past Warnings/Needs-discussion in one step — i.e., a `Suggestion` flagged by multiple roles becomes Needs-discussion, not Must-fix; only a `Warning` (or higher) flagged by multiple roles becomes Must-fix.
  - **Phase 5.** `/audit-team` is read-only and returns no fix plan of its own, and its per-role subagents cannot be asked follow-up questions once the run completes. If a finding needs more design input than its own text carries before the fixer can act on it, get that via a fresh same-tier dispatch (a new `general-purpose` or `--reviewer-model`-tier subagent, as appropriate) — never by re-invoking `/audit-team` (it is read-only, not a conversation) or expecting the completed team run to answer follow-ups.
  - **Phase 8's Round N+1 re-review is unaffected**: it already uses a single `general-purpose` agent regardless of `--reviewer`, so no adapter is needed there.
- If the value is a `<plugin>:<agent>` form: verify the plugin is installed. Check whether the plugin appears in the session's known skill list. If it does not appear, **fall back to `dual` and print a warning**: "Reviewer `<id>` not found — falling back to `dual` (feature-dev:code-reviewer + general-purpose). Install the plugin and retry if you want the specified reviewer." Pre-dispatch agent-name validation is not possible (Claude Code's agent surface is opaque until dispatch), so additionally: **if the plugin is installed but agent dispatch fails at runtime** (e.g. the agent name is misspelled or the agent no longer exists in the installed plugin version), treat the ID as unresolvable, apply the same fallback (`dual` for `--reviewer`, `general-purpose` for `--fixer`), and print a warning naming the failed dispatch — for example "Agent `<id>` dispatch failed — falling back to `<fallback>`. Verify the agent name against the installed plugin."
- If the value is `dual`: use `feature-dev:code-reviewer` + `general-purpose` in parallel. If `feature-dev` is not installed, fall back to `general-purpose` × 2 with two distinct briefs, with a warning naming the fallback. If `general-purpose` is also unavailable, **STOP and ask the user to install at least one reviewer plugin** — do NOT proceed with an empty reviewer set.
- If the value is `pair <a>+<b>` or `quad <a>,<b>,<c>,<d>`: validate each ID individually. When a slot is unresolvable, replace ONLY that slot with `general-purpose` and print a warning naming the unresolved slot (e.g. "Slot `<id>` not found — substituted `general-purpose`"). Do NOT collapse the full pair/quad to `dual`.
- The **same fallback rule applies to `--fixer`**. An unresolvable fixer ID falls back to `general-purpose` with a warning.
- When `--reviewer` is not `audit-team`, `--audit-team-args` is ignored. Print a warning: "`--audit-team-args` is set but `--reviewer` is `<value>`, not `audit-team` — ignoring `--audit-team-args`."

The fallback rule is uniform — it applies to any unknown agent ID, not only `feature-dev:code-reviewer`. The user is always told which ID was unresolvable and what was substituted.

### Phase 3 — Round-N review

Before composing the reviewer brief or validating `--reviewer-focus` tokens, load `references/reviewer-briefs.md` to obtain the per-target brief template AND the canonical `--reviewer-focus` token list. Use the loaded list to validate user-supplied tokens (recognized tokens override the default focus list; unrecognized-only tokens fall back with a warning).

Dispatch the reviewer per the rules in `dev-essentials:subagent-orchestration`. Do not restate those rules here — cross-reference them. Key dispatch decisions:

- **Foreground-parallel** when more than one reviewer is selected — issue multiple `Agent` calls within a single assistant message so they run concurrently (per `subagent-orchestration` Rule 3; there is no separate foreground/background choice for the `Agent` tool).
- **Single dispatch** for a single reviewer.

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

**Large-target orchestrated mode (optional):** when the target's diff exceeds roughly 2,000 lines or 30 files changed — or `--reviewer-focus` narrowing alone doesn't bring the read volume down enough — Phase 3 MAY use a context-budget-preserving orchestrator shape instead of briefing a reviewer with the full diff directly: dispatch a Target Explorer subagent (compact summary), then parallel per-area Codebase/Convention Explorer subagents (structured findings only, no raw diff/file content back to the orchestrator), then an optional Finding Verifier subagent, and finally read only the specific lines the surviving findings anchor to. This is a **mode, not a replacement** — for targets below that size, the default single/parallel reviewer dispatch above stays in effect. Full role definitions and prompt templates live in `references/orchestrated-review.md`.

### Phase 4 — Triage

**Finding-density check (before triage):** apply the density guardrail from the Guardrails section below — if the collected finding count is wildly disproportionate to that baseline, challenge the reviewer's result and request a stricter recheck before producing the triage table below, rather than triaging an inflated count at face value.

After collecting all reviewer output, produce a triage table before taking any action:

```text
Round <N> findings:
  Blocker:  <X>  (will fix; <Y> blocking)
  Critical: <X>  (will fix; <Y> blocking)
  High:     <X>  (will fix; <Y> blocking)
  Medium:   <X>  (deferred — --skip medium; <Y> blocking)
  Low:      <X>  (deferred — --skip low; <Y> blocking)
  Nit:      <X>  (deferred — --skip nit; <Y> blocking)

Proceeding to verify+fix <F> issues. Deferring <D>.
```

Apply `--skip` exactly: each severity token in `--skip` is its own independent gate — `--skip medium,low` defers Medium and Low but Nit remains eligible for fixing. When `--skip none` (the default), every severity row shows "(will fix)" and no "(deferred)" rows appear. Print the triage and **wait for the user to acknowledge** before starting Phase 5, unless `--auto-proceed` is set — in that case proceed immediately.

**Judge every finding on its merits, not on its label.** `--skip none` is the default precisely so nothing is auto-deferred unread — but it is not licence to mechanically fix everything either. For each finding, read what the reviewer actually concluded — its own **Must fix before merge** / **Acceptable risks** / **Needs discussion** call from the report's Conclusion section — instead of triaging off the severity label alone:

- A Medium that reintroduces a variant of the bug being fixed, or that leaves the fix's own regression uncovered, is worth fixing regardless of its label.
- A Low or Nit that is genuinely cosmetic is not — record it as deferred and move on.
- Where the fix is clear-cut, hand it to Phase 5 as normal. Where it is **not** confidently safe or scoped — it would need substantial refactoring, it touches a design decision, or the right resolution is genuinely ambiguous — do not decide unilaterally. Present that finding and the proposed fix(es) as a compact addendum to the triage (a short list, not a second review) and ask the user before the fixer touches it. This holds even under `--auto-proceed`: that flag suppresses the routine acknowledgment gate, never a genuine ambiguity.

**Record `blocking: true|false` on every finding, independent of its severity label.** Set `blocking: true` when Phase 4 concludes the finding must be resolved before merge: any Blocker/Critical/High by default, plus any Medium/Low/Nit the judgment above elevates. Set `blocking: false` for anything Phase 4 is content to record and move on from, including a Blocker/Critical/High the user and the session explicitly agreed to defer — in that case say so in the triage. The triage table's per-severity `(<Y> blocking)` counts are an aggregate view of this flag; Phase 8's `stop-clean` and Phase 9's deferred list read the per-finding flag itself, not that count or the severity label.

Findings deferred either way — by `--skip` or by the judgment above — are still recorded in Phase 9's deferred-items list.

For triage reference, the full severity-to-action mapping, and the `blocking` flag's full definition see `references/triage-matrix.md`.

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
  - **stop-clean**: BOTH of the following hold: (1) no unresolved finding within the re-review scope is `blocking: true` or carries severity Blocker/Critical/High, AND (2) no such finding appears in the deferred-items list across the entire run (whether deferred via `--skip`, marked PARTIAL/REJECT-then-deferred by the fixer, or deferred by Phase 4's merit judgment). Both halves of the test matter: `blocking: true` is Phase 4's own per-finding judgment, so a flagged Medium (or Low, or Nit) blocks `stop-clean` exactly as a High does; and the severity check reads the label, so an unflagged Blocker/Critical/High can never quietly clear the gate. If either condition fails, classify as `stop-max-rounds` instead.
  - **stop-max-rounds**: `--rounds` limit reached before a re-review pass could confirm clean — covers all four cases that prevent a `stop-clean` classification: (a) issues remain open in the re-review scope; (b) every finding was deferred via `--skip`; (c) every finding was fixed but no re-review round ran to confirm; (d) merge-blocking work is still outstanding anywhere in the run even though the rounds limit was not reached — either a deferred Blocker/Critical/High (via `--skip critical`, `--skip high`, etc.) or any unresolved finding Phase 4 marked `blocking: true`, at **any** severity label.
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
  Deferred: <count> (per --skip / merit triage)

### Round 2 (re-review of fix diff)
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
```

Any `(blocking)` row, and any deferred Blocker/Critical/High row, means the run could not classify `stop-clean` (see Phase 8).

---

## Output formats

### Brief format (printed to chat after every cycle)

Print unconditionally at the end of every cycle. Multi-cycle runs accumulate these into the final summary table in Phase 9.

```text
Cycle <N> — <target-summary>
  <count> findings: <Blk> Blocker, <Cri> Critical, <Hi> High, <Me> Medium, <Lo> Low, <Ni> Nit
  Triage: fix=<F>, deferred=<D> (per --skip / merit triage)
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

For targets too large to comfortably brief a single reviewer with (see Phase 3's "Large-target orchestrated mode"), `references/orchestrated-review.md` defines the alternative Target Explorer → Area Explorers → Finding Verifier → main-agent-synthesis dispatch shape.

## Verify+fix discipline

The verify+fix subagent's job is to filter unverified theories out of the fix pass. The detailed playbook — primary-source verification steps, APPLY/PARTIAL/REJECT decision tree, common rejection patterns, escalation policy for ambiguous findings — lives in `references/verify-fix-discipline.md`. Read it before dispatching the fixer.

## Guardrails

- **Never push by default.** Commits stay local; the user pushes when ready. The user can explicitly grant permission to push (e.g. "you can push after each fix commit") — only then.
- **Never touch unrelated files.** Only edit files named in the current triage, plus structurally required supporting files (see `references/verify-fix-discipline.md` §6 — covers e.g. the matching `*Tests.cs` for a missing-test-coverage finding, or the config registration file for a missing-config-knob finding). Do not extend into unrelated refactors.
- **Verify before confident fixes.** Apply only APPLY/PARTIAL-classified findings. REJECT means no edit. See `dev-essentials:engineering-discipline`.
- **Judge findings on their merits, not their labels.** `--skip none` is the default so nothing is auto-deferred unread; its counterpart obligation is Phase 4's per-finding judgment — recording `blocking: true|false` on every finding, escalating anything not confidently safe or scoped to the user before the fixer touches it, and letting Phase 8's `stop-clean` read that flag **in addition to** the Blocker/Critical/High severity guard, not instead of it — an unresolved `blocking: true` finding blocks `stop-clean` at any severity, and an unflagged Blocker/Critical/High blocks it too.
- **Be honest about uncertainty.** Flag ambiguous findings explicitly — as PARTIAL or REJECT with reasons — rather than silently ignoring or blindly applying them.
- **Don't over-fix.** Fix the identified issues only. This is not a refactoring session.
- **Respect `--rounds`.** Do not loop past the configured maximum. Report unresolved issues under "Deferred items" in the final summary.
- **Build/test verify is mandatory** unless `--dry-run` or `--no-verify-fix` is set. Any red signal after a fix round is owned by this skill session — investigate and fix, or escalate to the user.
- **Watch finding density.** A healthy density is roughly 1 Critical/High + 4 Medium + 3 Low/Nit per ~1,000 lines of diff or file content. Inflating finding counts to look thorough is anti-helpful. If Phase 4's collected count is wildly off that baseline (e.g. 15+ Mediums for a ~1,000-line target), challenge the reviewer's result and request a stricter recheck before triaging — do not accept an inflated count at face value.
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
| `dev-essentials:subagent-orchestration` | Dispatch rules (concurrent multi-`Agent`-call dispatch for independent reviewers/fixers — no separate foreground/background choice for the `Agent` tool) for Phase 3 reviewer dispatch and Phase 5 fixer dispatch. |
| `dev-essentials:process-pr-comments` | Tone and reply-format parallel — that skill acts on human reviewer comments; this skill runs the AI review cycle. They are complementary, not redundant. |
| `dev-essentials:github-mcp-conventions` | When `target=pr <id>`, use this skill's rules for calling `pull_request_read` with explicit `owner` and `repo`. |
