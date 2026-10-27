# Review-Reply Principles

These principles come from the series *How to Do Code Reviews Like a Human* by Michael Lynch (parts 1 and 2). This file adapts them to the **author side**, which is the side of this skill. The skill replies to reviewers for the author. Read this file before you write any reply.

## Contents

- Principles: applied to author-side replies
- Anti-patterns
- Quick sanity check before posting a reply

Contents: ten principles, the anti-patterns, and a short list of questions before you post a reply.

Source articles:

- <https://mtlynch.io/human-code-reviews-1/>
- <https://mtlynch.io/human-code-reviews-2/>

The examples below show the tone. The exact reply templates are in `commit-push-resolve.md` § "Reply templates" and in `automated-review-verification.md`.

## Principles — applied to author-side replies

### 1. Respect the scope of the review

Never edit lines outside the changelist of the PR, also where the comment of a reviewer hints at a wider fix. If the right fix touches lines that the PR does not touch, draft it, and show it to the human in chat. You can ask the human whether to open a follow-up PR or issue. Do not promise a follow-up in the thread reply (Bucket B in `SKILL.md`).

Applies to: every tagged comment. Reject expansions of the kind `just while I'm here`.

### 2. Frame replies as statements or requests, not commands

Say `we could rename this…`, not `rename this…`. Say `I've renamed X to Y`, not `you were right, fixed.` Do not use words that assign blame or make Claude the judge.

Example templates:

- Implementing: `**[AI]** Fixed: renamed TenantID → TenantId. Diff staged locally.`
- Pushing back: `**[AI][Draft]** Current shape preferred — the enclosing method owns the invariant. Happy to change if you see a case I'm missing.`

### 3. Prefer "we" over "you"

Use `we` for proposed changes, and `I` for actions that are done. Do not use `you` in feedback, in either direction. The shared framing keeps the review collaborative.

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

Template: `**[AI][Draft]** Optional — keeping current shape; happy to change if preferred. Reason: <one-line>.`

### 6. Limit feedback on repeated patterns

When the reviewer tags `[Repetition]` or when Claude notices it while reading adjacent threads, bundle the response: address the pattern once, list the other occurrences, and offer a single batched fix. Do not reply per-instance with the same note.

See `tag-actions.md` → `[Repetition]` workflow.

### 7. Offer sincere, specific praise when warranted

If a reviewer's comment significantly improves the code (better algorithm, catches a real bug, suggests a cleaner abstraction), acknowledge it in the reply. Keep it concrete. Name what the suggestion improved.

Bad: `Great suggestion, thanks!`
Better: `**[AI]** Applied — the switch to ReadOnlyMemory<T> removes the copy in the hot path. Good catch.`

Too much praise weakens the signal. Keep praise for suggestions that changed the outcome in a meaningful way.

### 8. Aim to bring the code up a grade, not to perfection

Accept "good enough" where more iterations do not make the code clearly better. A `[Suggestion]` or `[Optional]` change can be a lateral move. Then state the trade-off in the reply. The gates of `SKILL.md` § "Autonomy" and of `tag-actions.md` decide whether you implement the change or draft it. Do not implement it only by reflex.

### 9. Handle stalemates proactively

If a thread goes in circles, follow "Stalemate detection" in `SKILL.md`: stop the automatic replies, and show the thread to the human. Never keep replying to "win". That is how reviews break down.

### 10. Keep replies short

Defaults:

- Fix confirmation: 1 line.
- Draft answer: at most 3 lines. Link to the code. Do not paste it.
- Rejection / counter-proposal: ≤ 3 lines with one-line reasoning.

If the explanation needs more, put the detail in chat for the human. Keep the thread reply a pointer: `**[AI][Draft]** Pushing back — detail in session chat. Short version: <one-line>.`

## Anti-patterns

- **Defensive replies**, for example `I think you misread, the code actually does X.` Rephrase the reply as a shared question: `**[AI][Draft]** Reading this as X because of <line>. Want to compare notes?`
- **Stacking principles**. Three principles for one small change signal insecurity. Pick the most relevant one.
- **Apology padding**, for example `sorry for the confusion, my bad, I should have…`. Remove it entirely. State the fix or the reasoning.
- **Unsolicited improvements**. Code changes outside the comment of the reviewer, made `while you're at it`, bloat the PR and break the scope.
- **Narrating resolution in reply text**. The reply body states what was done: fixed, committed, or pushed. It does not also say "resolved" or "this is done now". The resolve call marks a thread as resolved, and the skill makes it only after the push of the fix landed (`SKILL.md` Phase 4). The thread state on GitHub carries that signal, not the words of the reply. For a thread that the skill leaves open on purpose (`commit-push-resolve.md` § "Which threads to resolve"), do not suggest a resolution at all.

## Quick sanity check before posting a reply

1. Does the reply stay within the PR's scope?
2. Is it phrased as a statement or request, not a command?
3. If it contains judgement, does it cite a principle or a verifiable anchor?
4. Is it ≤ 3 short lines (unless the reviewer asked for depth)?
5. Does it avoid narrating resolution in the reply text itself (letting the mechanical resolve action carry that signal instead)?
6. Is the `**[AI]**` or `**[AI][Draft]**` marker present?

If any answer is "no", rewrite the reply before posting.
