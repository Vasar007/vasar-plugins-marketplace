# Automated Review Verification

Read before replying to any comment carrying an automated review header (e.g., `AI Code Review`, `copilot:review`, `coderabbitai`, or a similar bot-generated heading). Automated review comments are the most failure-prone class of review feedback — they quote stale snippets, miss enclosing invariants, or flag code that is not reachable in production. Never trust the framing; always verify independently.

## What counts as an automated review comment

Any comment whose first non-empty line (or title) contains one of:

- `AI Code Review`
- `AIR` (as a standalone marker or short tag)
- `copilot:review` or similar GitHub Copilot review header
- A header/section that introduces the comment as coming from an automated review bot

If uncertain, err on the side of treating it as an automated review — the extra verification cost is cheaper than a bad auto-apply.

## Verification checklist

Run every step in order. Do not short-circuit, even for obviously trivial-looking notes.

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

Low confidence is a signal, not a failure. It tells the human the draft needs human judgement more than verification.

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

## Hard rules

- Never auto-implement an automated review fix, even with `verdict=valid` and `confidence=high`. A human must approve in chat or in the thread first.
- Never post the reply without the `**[AI][Draft]**` prefix and the closing draft-pending line.
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
