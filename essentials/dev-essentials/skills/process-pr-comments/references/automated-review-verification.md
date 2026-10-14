# Automated Review Verification

Read this file before you reply to a comment with an automated-review header. Examples: `AI Code Review`, `copilot:review`, `coderabbitai`, or a similar heading from a bot. Automated review comments fail more often than other review feedback. They quote old snippets, miss the invariants of the enclosing code, or flag code that production never reaches. Never trust the framing. Always test the finding on your own.

Contents: what counts as an automated review comment, the steps before a verdict, and the verdicts and confidence levels. Then the obviousness test, the reply templates, the hard rules, and the chat output.

## What counts as an automated review comment

Any comment whose first non-empty line (or title) contains one of:

- `AI Code Review`
- `copilot:review` or similar GitHub Copilot review header
- A header/section that introduces the comment as coming from an automated review bot

If you are not sure, treat the comment as an automated review. The extra work costs less than a bad automatic fix.

## Verification checklist

Run every step in order. Do not jump to a verdict before you read the code and widen the lens, also for a note that looks trivial. After you set the verdict and the confidence, § "Obviousness test (Phase 3b step 5)" decides what comes next: a direct implementation, a draft, or Stage 3 for `deep-fix`. The test decides what happens after these steps. It never allows you to skip them.

### 1. Re-read the actual code

Use the file path and the line range of the thread. Read the file at the latest iteration of the PR. The snippet that the bot quoted can be:

- Stale (from an earlier iteration).
- Truncated, hiding guards or early-returns.
- Decontextualized from the enclosing method.

### 2. Widen the lens

Read:

- The enclosing method and class.
- The direct callers. Search for the method name. If the class is injected, also read the DI composition.
- Any adjacent tests (same folder or mirrored test file).
- Feature-flag / options binding that gates this code path.

Many automated review comments flag local shapes that are correct in context because of an invariant enforced elsewhere.

### 3. Check production applicability

Ask:

- Is this code reachable under production configuration?
- Is it gated by a feature flag that is off in prod?
- Is it test-only (test project, `#if DEBUG`, `TestHost` wiring)?
- Does the proposed change alter the behavior that production shows, or only test and debug paths?

### 4. Check for false-positive signatures

Automated review tools commonly misfire on:

- Null checks before a member that the compiler already guarantees as non-null. Examples: a member after `Guard.Against.Null`, or a primary-constructor parameter with a non-null reference type.
- Async/await patterns already handled by a framework abstraction.
- Configuration access on options objects that FluentValidation rules already guard.
- "Possible exception" on paths already wrapped by a global exception handler or middleware.
- "Magic number" or "hardcoded string" comments on a value with a clear meaning, where a named constant does not help the reader.

If the flagged pattern matches one of these, the default verdict is `false-positive`, unless a new look at the code shows otherwise.

### 5. Assign a verdict

Use exactly one of:

| Verdict | Meaning |
| --- | --- |
| `valid` | The concern is real, and the proposed fix goes in the right direction. |
| `valid-but-narrow` | The concern is real, but the proposed fix misses a larger or better refactor. Plan the wider fix. The obviousness test decides whether you implement it or draft it. |
| `needs-clarification` | The code can be right or wrong. That depends on an intent of the author that the PR does not show. Ask a clarifying question. Do not apply a fix. |
| `false-positive` | The flagged code is correct. Cite the invariant, test, or configuration that makes it safe. |
| `not-applicable` | The pattern does not apply here, for example test-only code, a feature flag that is off, or a wrong framework abstraction. |

### 6. Assign confidence

| Level | When to use |
| --- | --- |
| `high` | The code, the tests, and an invariant all support the verdict. A human who reads the same evidence reaches the same conclusion. |
| `medium` | Code reading supports the verdict. The tests or the invariants are unclear or partial. |
| `low` | The verdict is a reasonable lean, but it depends on an intent that Claude cannot see. Treat the draft as a starting point, not a conclusion. |

Confidence is not a gate. A `low` confidence is a signal, not a failure (see § "Obviousness test (Phase 3b step 5)"). Confidence tells the human how much of the reply is judgement and how much is tested fact.

## Obviousness test (Phase 3b step 5)

The test applies only to the verdicts `valid` and `valid-but-narrow`. `needs-clarification`, `false-positive`, and `not-applicable` NEVER take this path, whatever their size. For them, go to `SKILL.md` Phase 3b step 6.

For `valid` and `valid-but-narrow`, the size of the fix does **not** matter. Ask one question: **does the right fix rewrite the target file or section from scratch, or redesign it at the same size**? If the answer is no, the change is a fix. A fix that meets all three conditions below gets a direct implementation:

- **It is a fix, not a redesign from the ground up**. Line count, file count, and "it touches more than one place" do **not** disqualify it. These are all fixes: a fix across several files, and a field threaded through a schema and its consumers. A stricter form of a rule that the code or the doc already states is a fix too. A missing case added to existing logic is a fix too. So is the end of a contradiction between two parts of the current change.
- **It stays inside the files and areas that the PR diff already touches**. It does not expand into new files or areas outside the scope. This is PR-scope discipline (Bucket B in `SKILL.md`).
- **It adds no NEW architecture and no NEW public contract**. Some changes fix an existing contract. Examples: documented behavior made to match reality, a stated rule made stricter, and a gap in existing logic closed. A mismatch between stated and actual behavior, corrected, is one too. These are not a change of architecture or contract. Only a mechanism or a contract that does not exist today fails this condition.

A fix that fails the second or the third condition goes to Phase 3b step 6, like the exception below. With `autonomous`, a fix that meets the second condition but fails the third is implemented without that stop. The cycle log lists it under "Decisions for your review" (Bucket A2 in `SKILL.md`).

**The exception: the only reason of size to decline a direct implementation**. Go to step 6 for a fix that rewrites the target file or section from scratch. A redesign that is just as basic counts too. Both parts must hold. (a) The reviewer asks for a different mechanism that has **no precedent anywhere in this codebase**. AND (b) there are **several materially different ways to build it**, and nothing in the existing code chooses between them. Two examples still need a draft. The first is "replace the whole polling design with an event-driven one" in a codebase with no event infrastructure. The second is "split this into three separate commands", where the split boundary is truly open. Nothing in the list of the first condition reaches this bar.

**Second exit: `deep-fix`**. If `deep-fix` names this thread, the exception goes to Stage 3 instead of step 6 (see `deep-fix.md`). `/research-implement-review-report` exists for a finding at rewrite-from-scratch size: it researches the precedent, shows the design choice for sign-off, implements, and reviews. The verdicts `needs-clarification`, `false-positive`, and `not-applicable` stay ineligible for `deep-fix`.

**Confidence is not a gate. It changes what you SAY, not what you DO**. With `confidence: high`, implement and reply. With `medium` or `low`, or with doubt about the RIGHT approach (not about whether to fix), **still implement your best fix**. Also state the doubt as an explicit question in the chat report and in the thread reply: `Implemented <X>. Open question: <the specific choice you made and the alternative>. Say the word and I'll switch.` **Ask AND fix**. Confidence never stops the fix. Only a failed condition or the exception stops it. Do not mix this up with the `needs-clarification` verdict. That verdict is about whether a defect exists at all, and the skill never implements it.

If the conditions hold, treat the finding like `[ToFix]`: implement, commit (Phase 4), and post a non-draft `**[AI]**` reply with the "Implemented fix" template below. This path has no draft stage.

## Draft reply templates

Each verdict has one draft template. Change the rationale, and keep the structure. Post each template in the full form of `commit-push-resolve.md` § "Reply templates": the marker and the T# link tag on the first line, then a blank line, then the rest of the template.

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

Use this template for a `valid` or `valid-but-narrow` finding that passes the obviousness test. It is the default path for a valid finding, not a narrow fast lane. Size and file count do not matter. With `medium` or `low` confidence, use the same template, and add the open question to the body. It is the "Implemented fix" template of `commit-push-resolve.md` § "Reply templates", word for word:

```text
**[AI]** **[[T#<commentId>](<html_url>)]**

Fixed: <one-line summary>. Committed as <short-sha>; will be included in the next push.
```

This path has no `**[AI][Draft]**` prefix and no draft-pending line. The fix is already committed, not proposed.

## Hard rules

- **A direct implementation of an automated-review fix needs BOTH a `valid` or `valid-but-narrow` verdict AND a passed obviousness test**. The test is in § "Obviousness test (Phase 3b step 5)". A fix that fails the test needs the approval of a human, in chat or in the thread, before any edit. Two exceptions apply to the rewrite-from-scratch exception of the test. With `autonomous`, it goes ahead without that approval (Bucket A2 in `SKILL.md`). If `deep-fix` names this thread, it goes to Stage 3 instead (`deep-fix.md`). With `autonomous`, a fix that fails only the third condition (new architecture or new public contract) also goes ahead without that approval, and the cycle log lists it under "Decisions for your review". `needs-clarification`, `false-positive`, and `not-applicable` never get a direct implementation or `deep-fix`, because they have no fix to make.
- Every **draft** reply (the draft templates above) must carry the `**[AI][Draft]**` prefix and the closing draft-pending line. The "Implemented fix" reply above is a completed action, not a draft, and intentionally does not carry either.
- Never shorten the rationale. The reviewer must see the reasoning that led to the verdict, not only the verdict.
- The steps above can find a DIFFERENT issue next to the concern of the bot, for example a real bug or a missed null case. Do NOT broaden the reply silently. Show the second finding to the human in chat, and ask whether to mention it in the thread.

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
