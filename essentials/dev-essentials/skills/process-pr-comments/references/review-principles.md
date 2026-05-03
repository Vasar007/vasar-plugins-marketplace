# Review-Reply Principles

Distilled from Michael Lynch's *How to Do Code Reviews Like a Human* series (parts 1 and 2) and adapted for the **author-side** workflow this skill performs. Read before composing any reply.

Source articles:

- <https://mtlynch.io/human-code-reviews-1/>
- <https://mtlynch.io/human-code-reviews-2/>

## Why this exists

The skill replies to reviewers *on behalf of the author*. Every reply is part of the same social contract as a human review — tone, framing, and scope matter. A technically correct reply with poor framing still damages the review relationship.

## Principles — applied to author-side replies

### 1. Respect the scope of the review

Never edit lines outside the PR's changelist, even when a reviewer's comment hints at a wider fix. If the right fix would touch untouched lines, draft it, surface to the human, and offer to open a follow-up PR or work item.

Applies to: every tagged comment. Reject "just while I'm here" expansions.

### 2. Frame replies as statements or requests, not commands

Say "we could rename this…" rather than "rename this…". Say "I've renamed X to Y" rather than "you were right, fixed." Avoid language that assigns blame or positions Claude as the judge.

Example templates:

- Implementing: `[AI] Fixed: renamed TenantID → TenantId. Diff staged locally.`
- Pushing back: `[AI][Draft] Current shape preferred — the enclosing method owns the invariant. Happy to change if you see a case I'm missing.`

### 3. Prefer "we" over "you"

Use `we` for proposed changes, `I` for actions already taken. Avoid `you` entirely when giving or receiving feedback. The collective framing keeps reviews collaborative.

Bad: `You're missing a null check.`
Better: `We should add a null check before dereferencing.`
Best (author reply): `Added the null check.`

### 4. Tie judgement to a principle, not preference

When explaining *why* a change (or a refusal to change), cite the underlying principle. Prefer verifiable anchors:

- A named design principle (SRP, DRY, YAGNI, open/closed).
- A project convention (`.editorconfig`, `.claude/rules/`, existing pattern in adjacent files).
- An invariant enforced elsewhere (a test, a validator, a DI guard).
- A measurable budget (allocation count, request latency).

Bad: `This looks cleaner.`
Better: `This split mirrors the pattern in Sessions/SessionRepository.cs and matches the repo convention.`

### 5. Don't withhold approval for trivia

`[Optional]` and `[Suggestion]` must never be treated as blockers. When declining, the reply language explicitly acknowledges the optional status and the reviewer's autonomy.

Template: `[AI][Draft] Optional — keeping current shape; happy to change if preferred. Reason: <one-line>.`

### 6. Limit feedback on repeated patterns

When the reviewer tags `[Repetition]` or when Claude notices it while reading adjacent threads, bundle the response: address the pattern once, list the other occurrences, and offer a single batched fix. Do not reply per-instance with the same note.

See `tag-actions.md` → `[Repetition]` workflow.

### 7. Offer sincere, specific praise when warranted

If a reviewer's comment significantly improves the code (better algorithm, catches a real bug, suggests a cleaner abstraction), acknowledge it in the reply. Keep it concrete — name what the suggestion improved.

Bad: `Great suggestion, thanks!`
Better: `[AI] Applied — the switch to ReadOnlyMemory<T> removes the copy in the hot path. Good catch.`

Overuse dulls the signal; reserve for suggestions that meaningfully changed the outcome.

### 8. Aim to bring the code up a grade, not to perfection

Accept "good enough" when further iteration would not meaningfully improve the code. For `[Suggestion]` / `[Optional]` threads where the proposed change is a lateral move, explain the trade-off and let the human decide rather than implementing reflexively.

### 9. Handle stalemates proactively

If a thread has > 3 back-and-forth replies and the latest two are unresolved disagreement, stop replying automatically. Surface to the human in chat: "This thread is going in circles — consider talking it out synchronously or requesting a design review."

Never keep replying to "win" — that is how reviews break down.

### 10. Keep replies short

Defaults:

- Fix confirmation: 1 line.
- Draft answer: ≤ 3 lines; link to code instead of pasting.
- Rejection / counter-proposal: ≤ 3 lines with one-line reasoning.

If the explanation genuinely needs more, put the detail in chat for the human, and keep the thread reply a pointer: `[AI][Draft] Pushing back — detail in session chat. Short version: <one-line>.`

## Anti-patterns

- **Defensive replies** — "I think you misread, the code actually does X." Rephrase as a collaborative check: `[AI][Draft] Reading this as X because of <line>. Want to compare notes?`
- **Stacking principles** — citing three principles to justify one small change signals insecurity. Pick the most relevant one.
- **Apology padding** — "sorry for the confusion, my bad, I should have…". Remove entirely; state the fix or reasoning.
- **Unsolicited improvements** — making code changes outside the reviewer's comment "while you're at it" bloats the PR and violates scope.
- **Claiming resolution** — the author (or Claude on their behalf) never says "resolved". The reviewer decides.

## Quick sanity check before posting a reply

1. Does the reply stay within the PR's scope?
2. Is it phrased as a statement or request, not a command?
3. If it contains judgement, does it cite a principle or a verifiable anchor?
4. Is it ≤ 3 short lines (unless the reviewer asked for depth)?
5. Does it avoid claiming the thread is resolved?
6. Is the `[AI]` / `[AI][Draft]` marker present?

If any answer is "no", rewrite the reply before posting.
