# Automated Review Verification

Read before replying to any comment carrying an automated review header (e.g., `AI Code Review`, `copilot:review`, `coderabbitai`, or a similar bot-generated heading). Automated review comments are the most failure-prone class of review feedback — they quote stale snippets, miss enclosing invariants, or flag code that is not reachable in production. Never trust the framing; always verify independently.

## What counts as an automated review comment

Any comment whose first non-empty line (or title) contains one of:

- `AI Code Review`
- `copilot:review` or similar GitHub Copilot review header
- A header/section that introduces the comment as coming from an automated review bot

If uncertain, err on the side of treating it as an automated review — the extra verification cost is cheaper than a bad auto-apply.

## Verification checklist

Run every step in order — do not skip straight to a verdict without reading the code and widening the lens first, even for obviously trivial-looking notes. Once a verdict and confidence are assigned, SKILL.md Phase 3b's obviousness test decides whether this note qualifies for the implement-and-reply path instead of the draft-and-ping path below; that test is a gate on WHAT HAPPENS AFTER verification, not a license to skip verification itself. Note the test's bar: a `valid`/`valid-but-narrow` finding is implemented directly unless the right fix would mean **rewriting the target from scratch or a redesign of equivalent magnitude** — size, file count, and less-than-high confidence do not divert a finding to the draft path. When the right fix DOES hit that bar, the exception's fall-through has a second exit: if `deep-fix=<threadId>` names this thread, it routes to Stage 3 (`SKILL.md` § "Dispatch model" and Phase 4's "Stage 3 — `deep-fix` brief and outcomes") instead of the draft-and-ping path below — SKILL.md Phase 3b step 5's second exit. The three non-actionable verdicts (`needs-clarification` / `false-positive` / `not-applicable`) stay ineligible for either path — there is no fix to implement, draft, or route.

### 1. Re-read the actual code

Use the thread's file path and line range. Read the file at the PR's latest iteration. The snippet the bot quoted may be:

- Stale (from an earlier iteration).
- Truncated, hiding guards or early-returns.
- Decontextualized from the enclosing method.

### 2. Widen the lens

Read:

- The enclosing method and class.
- Direct callers (grep for the method name; check DI composition if it is injected).
- Any adjacent tests (same folder or mirrored test file).
- Feature-flag / options binding that gates this code path.

Many automated review comments flag local shapes that are correct in context because of an invariant enforced elsewhere.

### 3. Check production applicability

Ask:

- Is this code reachable under production configuration?
- Is it gated by a feature flag that is off in prod?
- Is it test-only (test project, `#if DEBUG`, `TestHost` wiring)?
- Would the proposed change alter observable prod behavior or only test/debug paths?

### 4. Check for false-positive signatures

Automated review tools commonly misfire on:

- Null checks before a member the compiler already guarantees non-null (e.g., after a `Guard.Against.Null`, primary-constructor parameter with non-null reference type).
- Async/await patterns already handled by a framework abstraction.
- Configuration access on options objects already validated by FluentValidation.
- "Possible exception" on paths already wrapped by a global exception handler or middleware.
- "Magic number" / "hardcoded string" comments on values that have a clear semantic meaning and a named constant would not improve readability.

If the flagged pattern matches one of these, the default verdict is `false-positive` unless re-verification proves otherwise.

### 5. Assign a verdict

Use exactly one of:

| Verdict               | Meaning                                                                                                                 |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------|
| `valid`               | Concern is real and the proposed fix is the right direction.                                                            |
| `valid-but-narrow`    | Concern is real, but the proposed fix misses a larger or better refactor. Draft the wider fix.                          |
| `needs-clarification` | Code could go either way depending on author intent not visible in the PR. Ask a clarifying question rather than apply. |
| `false-positive`      | The flagged code is correct. Cite the invariant, test, or config that makes it safe.                                    |
| `not-applicable`      | Pattern does not apply here (test-only, feature-flagged off, wrong framework abstraction assumed, etc.).                |

### 6. Assign confidence

| Level    | When to use                                                                                                                      |
|----------|----------------------------------------------------------------------------------------------------------------------------------|
| `high`   | Verdict verified by code + tests + invariant. A human reading the same evidence would reach the same conclusion.                 |
| `medium` | Verdict supported by code reading; tests or invariants unclear or partial.                                                       |
| `low`    | Verdict is a reasonable lean but depends on intent not visible to Claude. Treat the draft as a starting point, not a conclusion. |

Low confidence is a signal, not a failure, and it is **not** a stop. On a `valid`/`valid-but-narrow` finding it does not divert to the draft path — per SKILL.md Phase 3b step 5, the fix is implemented anyway and the uncertainty is stated as an explicit question in the reply and in the chat report ("ask AND fix"). What confidence tells the human is how much of the reply is judgement rather than verified fact.

## Draft reply templates

Each verdict has a canonical draft. Customize the rationale; keep structure.

### `valid`

```text
**[AI][Draft]** Verdict: valid — concern applies here.

Rationale: <one-line why the concern holds, anchored to code>.
Proposed fix: <one-line description>. Diff ready to apply on your approval.

Confidence: high | medium | low.

*Draft pending author confirmation.*
```

### `valid-but-narrow`

```text
**[AI][Draft]** Verdict: valid-but-narrow — concern is real, but the suggested fix misses the broader case.

Rationale: <why the narrow fix is incomplete>.
Wider proposal: <one-line description of the better fix>.

Confidence: high | medium | low.

*Draft pending author confirmation.*
```

### `needs-clarification`

```text
**[AI][Draft]** Verdict: needs-clarification — cannot decide from code alone.

Question: <one clarifying question about author intent>.

Confidence: low (intent-dependent).

*Draft pending author confirmation.*
```

### `false-positive`

```text
**[AI][Draft]** Verdict: false-positive — flagged code is correct.

Rationale: <cite the invariant, test, config, or validator>.
Reference: <file:line or test name>.

Confidence: high | medium | low.

*Draft pending author confirmation.*
```

### `not-applicable`

```text
**[AI][Draft]** Verdict: not-applicable — pattern does not apply to this code path.

Rationale: <why — test-only, feature-flagged off, wrong framework abstraction, etc.>.

Confidence: high | medium | low.

*Draft pending author confirmation.*
```

### Implemented fix — the default path for a valid finding

Used whenever `verdict` is `valid` / `valid-but-narrow` AND SKILL.md Phase 3b's obviousness test passes — the DEFAULT path for a valid finding, not a narrow fast lane. Size and file count are irrelevant to it, and `medium`/`low` confidence uses this same template with the open question appended to the body. This is the same "Implemented fix" template SKILL.md uses for `[ToFix]` — reused verbatim rather than invented here:

```text
**[AI]** **[[T#<commentId>](<html_url>)]**

Fixed: <one-line summary>. Committed as <short-sha>; will be included in the next push.
```

No `[AI][Draft]` prefix and no draft-pending line on this path — the fix is already committed, not proposed.

## Hard rules

- **Implementing an automated-review fix directly requires BOTH `verdict` in `valid`/`valid-but-narrow` AND passing SKILL.md Phase 3b's obviousness test.** What that test actually rules out is narrow: a fix reaching outside the current PR's diff, a fix that introduces a genuinely new architecture or public contract, and a fix that would mean rewriting the target from scratch (or an equivalently fundamental redesign with no codebase precedent and no basis for choosing between several ways to build it). It does **not** rule out multi-file fixes, threading a field through a schema, tightening an already-stated rule, closing a gap in existing logic, or a `confidence: medium`/`low` verdict — those are implemented, with any uncertainty about the approach stated as a question in the same reply. Only when the test's rewrite-from-scratch exception applies does a human have to approve in chat or in the thread before any edit — or, if `deep-fix` names this thread, route it through `/research-implement-review-report` instead of waiting on chat/thread approval (SKILL.md Phase 3b step 5's second exit). Verdicts `needs-clarification` / `false-positive` / `not-applicable` are never eligible for either the direct-implement path or `deep-fix` — there is no actionable fix in those cases, `deep-fix` or not.
- Every **draft** reply (the draft templates above) must carry the `**[AI][Draft]**` prefix and the closing draft-pending line. The "Implemented fix" reply above is a completed action, not a draft, and intentionally does not carry either.
- Never truncate the rationale — the reviewer should see the reasoning that led to the verdict, not just the verdict.
- If verification uncovers a DIFFERENT issue adjacent to the bot's concern (genuine bug, missed null case), do NOT silently broaden the reply. Surface the secondary finding in chat to the human and ask whether to mention it in the thread.

## Chat output alongside the thread reply

Every verdict also gets logged in the chat for the human:

```text
T#17 [AutoReview] Domain/User.cs:88
  Verdict: false-positive (confidence: high)
  Rationale: null-check unreachable after Guard.Against.Null on line 84.
  Draft posted: yes.
  Awaiting: human approval before any code change.
```

This lets the human skim verdicts without opening every thread.
