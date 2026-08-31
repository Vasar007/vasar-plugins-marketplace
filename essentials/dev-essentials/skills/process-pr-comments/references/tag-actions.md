# Tag Action Matrix

Authoritative per-tag behavior for `process-pr-comments`. Read this file whenever a classification lands on a tag and the short summary in `SKILL.md` is not enough.

Tag parsing: leading bracketed tokens at the very start of the comment (e.g., `[ToFix]`, `[P1][Performance]`). Multiple tags combine — apply the strictest action. An automated review comment (e.g., from `github-actions[bot]`, `copilot[bot]`, `coderabbitai[bot]`, or any configured automated reviewer) takes precedence over any tag and routes to `automated-review-verification.md`.

## Size thresholds for autonomy

Used by `[ToFix]`, `[Performance]`, `[PX]`, and "trivial" `[Suggestion]` / `[Optional]`.

- **Small** — ≤ 20 LoC changed, single file, no public API change (signatures, DTOs, exposed types), no new dependencies, no test refactor. Safe to implement.
- **Medium / Large** — anything larger, or touching public APIs, DI wiring, EF migrations, string resources, swagger specs. Always draft and wait — or, if the invocation names the thread with `deep-fix=<threadId>`, route it through `/research-implement-review-report` instead (SKILL.md § "Dispatch model" Stage 3 and Phase 3's `deep-fix` override).
- **Architectural** — reserved for changes at **rewrite-from-scratch magnitude**: the reviewer is asking for a fundamentally different mechanism with no precedent in this codebase, and there are several materially different ways to build it with nothing in the existing code to choose between them. Always draft; consider suggesting a design review — or, with `deep-fix` naming the thread, route it through `/research-implement-review-report` (same pointer as the Medium/Large row above). Merely adding, moving, or renaming a type across projects is **not** this level on its own — that is a Medium/Large fix, judged on the row above.

`strict` flag treats every category as "draft and wait". `deep-fix` is a per-thread override the human supplies at invocation, not a category `strict` or the size thresholds pick automatically — see SKILL.md Phase 3's `deep-fix` override for the full eligibility rule.

## Tags

### `[ToFix]`

The reviewer requires a change. The PR will not be approved without it.

- Small: implement edit → verify build/tests → commit (eager, no approval needed — Phase 4) → reply immediately, referencing the local commit SHA: `**[AI]** Fixed: <one-line summary>. Committed as <short-sha>; will be included in the next push.` Push is a separate, later, per-cycle step gated by explicit approval (see Phase 4) — unless `auto-push`/`autonomous` is set. Pass `no-commit` to stage only instead.
- Medium / Large: prepare the diff in chat, explain the approach, wait for the human's explicit go-ahead — or, if `deep-fix=<threadId>` names this thread, route it through `/research-implement-review-report` instead (SKILL.md's `deep-fix` override). Do not edit files.
- After implementation, the thread stays open until its commit's push actually lands. Once it does, the skill resolves the thread itself via `mcp__plugin_github_github__pull_request_review_write` (`method: resolve_thread`) (Phase 4) — no manual GitHub UI step needed for a fix this skill made.

Example (small):

> Reviewer: `[ToFix] Rename FooID to FooId — matches the rest of this file.`
>
> Action: edit the file, verify build/tests, commit, reply: `**[AI]** Fixed: renamed FooID → FooId. Committed as a1b2c3d; will be included in the next push.`

### `[Performance]`

Identical workflow to `[ToFix]` with two additions:

1. In the reply, note any observable effect ("inner loop tightened, removes N allocations per request").
2. If tests or benchmarks exist near the change, run them locally and include the result in the chat log. If none exist, surface that: "No benchmark covers this path — consider adding one if this is hot code."

Never mark a `[Performance]` thread as done silently; always state what you changed and what you did not measure.

### `[PX]` (`[P1]`, `[P2]`, `[P3]`, …)

Priority marker, not an action class. The underlying action comes from the co-tag (e.g. `[P1][ToFix]`). If `[PX]` appears alone, treat as `[ToFix]` at the stated priority.

Priority ordering:

- `P1` / `P2`: process first each cycle; never defer.
- `P3` and higher: safe to defer behind lower-priority work but do not ignore.

### `[Suggestion]`

A concrete improvement. PR approval is not blocked.

- Trivial + small: implement like `[ToFix]`. Reply `**[AI]** Applied suggestion: <summary>. Committed as <short-sha>; will be included in the next push.`
- Non-trivial: draft the trade-off in chat and post a `**[AI][Draft]**` reply summarizing pros/cons. Example reply: `**[AI][Draft]** Option A keeps the current shape; option B inlines the helper. Current preference: A because <one-line reason>. Happy to switch — your call.`

### `[Optional]`

Very close to `[Suggestion]` but weaker: "do this if easy, otherwise skip."

- Trivial + small: implement and reply with explicit "optional accepted" language: `**[AI]** Applied optional suggestion: <summary>. Committed as <short-sha>; will be included in the next push.`
- Otherwise: reply `**[AI][Draft]** Optional — keeping current shape; happy to change if preferred. Reason: <one-line>.` No code edit.

Never block on `[Optional]`. Never push back hard — the mtlynch rule "don't withhold approval for trivia" applies here symmetrically.

### `[Question]`

The reviewer wants an explanation. Authorship risk is real — a wrong public answer over the author's identity can mislead reviewers. Never post a `[Question]` reply without an explicit human go-ahead.

- Read the relevant code before answering. Do not synthesize from the comment alone.
- Draft format: claim + reasoning + citation (file and line range, existing test, or linked documentation).
- Show the draft to the human in chat first. Ask: `Post this [Question] reply to T#<thread-id>? (yes / edit / skip)`.
- Only after `yes` → post `**[AI][Draft]** <answer in 1–3 short sentences>. See <file:line> / <test> / <doc link>.\n\n*Draft pending author confirmation.*`
- On `edit` → incorporate the human's revision and ask again.
- On `skip` → record the decision in `processedCommentIds` with `action: "drafted"` and `replyPosted: false`; do not post.
- If the answer is "I don't know", say so; surface the uncertainty in chat and ask the human rather than posting speculation.

### `[ToDiscuss]`

The reviewer wants a conversation, not a fix. Never edit code.

- Summarize the positions in chat: the reviewer's concern, your reading of the trade-off, a proposed direction.
- Do NOT post a thread reply automatically. Surface to the human with: "This thread is tagged `[ToDiscuss]` — want me to draft a reply or wait for you to respond?"
- If the user asks, post a measured reply that frames options and tags uncertainty.

### `[OutOfScope]`

Never implement in the current PR. The comment either records a concern or asks for follow-up tracking.

Decision tree:

1. Reviewer is just noting it → reply `**[AI]** Noted, out of scope for this PR.` No further action.
2. Reviewer asks to track separately (phrases: "track it", "open a ticket", "file an issue", "separate PR", "TODO") → delegate to the Task Composer agent.

Issue flow:

1. Invoke Task Composer (`dev-essentials:task-composer`) in `mode: response` with a concise brief: the comment text, the file/line, why it is out of scope, and any priority hint from co-tags. Task Composer drafts title and description in chat — no file written, no GitHub call yet.
2. Confirm title and type with the user. This step is never bypassed, `autonomous` or not — see SKILL.md § Autonomy, Bucket B.
3. On user approval, re-invoke Task Composer with `mode: create` and the confirmed fields plus `owner` and `repo` (required by Task Composer; pass verbatim, never infer — see `dev-essentials:github-mcp-conventions` Rule 1). Task Composer handles the full create → link (when a parent is given) → verify flow and returns the verified ID and URL. Never call `mcp__plugin_github_github__issue_write` directly from this skill.
4. Use ONLY the verified ID and URL returned by Task Composer. Reply `**[AI]** Tracked as issue #<id>: <title>.`

If the user declines or wants to defer → reply `**[AI]** Noted — will not track separately yet.` No issue.

### `[Note]` and untagged comments

Informational. No code edit. No thread reply.

- Summarize in chat so the human sees the note.
- Skip the dedup set ONLY if the `tags` param excludes Note; otherwise add to `processedCommentIds` so it is not re-surfaced next cycle.
- If the note appears to contain hidden action ("btw, should we refactor X?"), surface the ambiguity and ask the human whether to re-classify as `[Suggestion]` or `[Question]`.

### `[Repetition]`

The reviewer has flagged a pattern seen multiple times; the `[Repetition]` tag signals "fix the whole pattern, not just this instance."

1. Resolve the underlying tag (usually `[ToFix]` or `[Suggestion]`).
2. Find all occurrences of the pattern in the PR's diff (NOT outside it — respect scope).
3. Present the pattern and the occurrence list in chat: "Found N occurrences. Apply the pattern fix across all?"
4. On user approval: implement across all occurrences, commit (eager, Phase 4), reply `**[AI]** Fixed pattern across N occurrences: <summary>. Committed as <short-sha>; will be included in the next push.`
5. Without approval: fix only the flagged instance and reply `**[AI]** Fixed this instance. Waiting on your call for the remaining N−1.`

### Automated review comments (special case)

Takes precedence over tags. See [`automated-review-verification.md`](automated-review-verification.md). Summary:

- Always re-verify independently. Do not trust the bot's framing.
- Land on a verdict: `valid` / `valid-but-narrow` / `needs-clarification` / `false-positive` / `not-applicable`.
- `valid` / `valid-but-narrow` findings are implemented and committed directly, like `[ToFix]`, whenever SKILL.md Phase 3b's obviousness test passes — in-diff, no NEW architecture or public contract, and not a rewrite-from-scratch-magnitude redesign. **The size thresholds above do not apply to this path**: multi-file fixes, schema-threading fixes, contract-tightening fixes, and `confidence: medium`/`low` verdicts are all implemented (with the open question stated in the same reply — "ask AND fix"). See SKILL.md Phase 3b and `automated-review-verification.md`'s "Implemented fix" template. Only Phase 3b step 5's rewrite-from-scratch exception, or a `needs-clarification`/`false-positive`/`not-applicable` verdict, posts an `**[AI][Draft]**` reply and waits for human approval — unless `deep-fix` names the thread, in which case the rewrite-from-scratch exception's fall-through routes to Stage 3 instead (SKILL.md Phase 3b step 5's second exit). `needs-clarification` / `false-positive` / `not-applicable` verdicts are never eligible for `deep-fix` either — there is no actionable fix to route in those cases.

## When multiple tags combine

Use the strictest action among them:

- `[P1][ToFix]` → treat as `[ToFix]` with priority P1 (process first).
- `[Optional][Suggestion]` → treat as `[Optional]` (weakest action); reply language emphasizes "optional".
- `[Repetition][ToFix]` → `[Repetition]` workflow; the underlying tag is `[ToFix]`.
- `[OutOfScope][Suggestion]` → `[OutOfScope]` workflow (never implement in current PR); use suggestion text to inform the follow-up issue brief.
- `[Performance][ToFix]` → `[Performance]` workflow (explicit effect note in reply).

## Fall-back rules

- Cannot parse any tag → `[Note]`.
- Cannot determine size category → treat as Medium (draft, do not implement).
- Cannot read the file referenced by `threadContext` (e.g., renamed, moved) → do NOT guess. Surface to the human in chat and leave the comment unprocessed for the next cycle.
