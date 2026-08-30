# Thread State Schema

In-session state the `process-pr-comments` skill keeps to avoid reprocessing comments across polling cycles, and the cycle-log format printed to the user. State is session-local — a fresh `/loop` session starts empty and relies on GitHub thread state (reply text, thread state) to detect previously-handled comments.

## `processedCommentIds` — dedup set

A plain set of GitHub comment IDs that have been fully handled this session.

Entry shape (logical; implementation is whatever is ergonomic for Claude in the turn):

```json
{
  "pullRequestNumber": 42,
  "commentId": 92,
  "tag": "ToFix",
  "action": "fixed",
  "verdict": null,
  "confidence": null,
  "replyPosted": true,
  "replyCommentId": 93,
  "editedFiles": ["path/to/Auth.cs"],
  "issueNumber": null,
  "cycleNumber": 3,
  "timestamp": "2026-04-20T15:42:11Z"
}
```

Rules for writing to the set:

- Add an entry ONLY after the comment's action (or explicit skip decision) completes without error.
- On transient failure (MCP timeout, file write rejected), leave the comment unprocessed so the next cycle retries.
- Skipping because of the `tags` param filter is NOT an "explicit skip" — do NOT add the comment to the set, because a later invocation with different `tags` should revisit it.
- Skipping because of `[Note]` / untagged with no action IS an "explicit skip" — add to the set with `action: "noted"`.

Fields:

| Field              | Required | Notes                                                                                                                                                                                                                                                   |
|--------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `pullRequestNumber` | yes      | Sanity check in case the user re-invokes with a different PR mid-session (the skill stops and asks rather than mixing state).                                                                                                                            |
| `commentId`        | yes      | GitHub comment ID returned by `pull_request_read`.                                                                                                                                                                                                      |
| `tag`              | yes      | The primary tag applied (or `AutoReview` / `Note`).                                                                                                                                                                                                     |
| `action`           | yes      | One of `fixed`, `drafted`, `noted`, `tracked`, `skipped`. `skipped` is written only for explicit terminal skips (e.g., file missing/moved, user answered "skip" on a `[Question]` confirm prompt) — never for `tags`-filter exclusions.                |
| `verdict`          | AutoReview only | One of the five verdicts from `automated-review-verification.md`.                                                                                                                                                                                  |
| `confidence`       | AutoReview only | `high` / `medium` / `low`.                                                                                                                                                                                                                         |
| `replyPosted`      | yes      | `false` when `dry-run` / `no-reply` is on.                                                                                                                                                                                                              |
| `replyCommentId`   | optional | ID returned by `add_reply_to_pull_request_comment` — useful for user reference.                                                                                                                                                                         |
| `editedFiles`      | optional | List of files touched by this action. Empty for drafts/notes.                                                                                                                                                                                           |
| `issueNumber`      | optional | Set when `[OutOfScope]` tracking produced a GitHub issue.                                                                                                                                                                                               |
| `cycleNumber`      | yes      | Starts at 1, increments each cycle.                                                                                                                                                                                                                     |
| `timestamp`        | yes      | ISO 8601 UTC when the action completed.                                                                                                                                                                                                                 |

## Committed-fix detection — re-derived every cycle, not persisted

There is no persisted "pending resolution" entry for a committed-but-unpushed fix.
SKILL.md Phase 2 step 5 re-derives that fact fresh every cycle, straight from
GitHub's own thread/reply history and real git ancestry
(`git merge-base --is-ancestor`), so there is nothing to keep in sync and
nothing that can survive in a corrupted or half-written state.

This file documents ONLY the reply-text matching conventions Phase 2 step 5 uses to
recognize an affirmative commit claim. For the actual branch/decision logic — what happens
for each `assessedState` (`fresh-unhandled` / `cured` / `unconfirmed-commit-claim` /
`already-assessed`), the newer-reply guard, and the `autonomous`/`dry-run`/`no-reply`
gating — see **SKILL.md Phase 2 step 5**; it is not re-derived here.

Note that in normal operation this whole re-derivation runs rarely: Phase 2's own
pre-filter (SKILL.md Phase 2 step 2) already skips any thread whose `isResolved` is `true`
— a real field returned by `pull_request_read`'s `get_review_comments` method — before the
thread ever reaches the roster this section's logic runs against. This section's
re-derivation exists for the threads that pre-filter does NOT catch: a fix committed and
replied to but not yet pushed (so GitHub doesn't know about it yet), or a push that landed
but whose `resolve_thread` call failed or was never attempted (an old reply predating this
skill's resolve support, for instance).

**Affirmative commit claim — what counts.** A tightened match, not a loose prefix match:
any `**[AI]**` (or legacy plain `[AI]`) reply carrying the phrase "Committed as `<sha>`"
or "commit `<sha>`" adjacent to the fix summary. An intervening `**[[T#<id>](<url>)]**`
tag between the `**[AI]**` marker and the body is expected and irrelevant to the match.

- Positive match: `**[AI]** Fixed: renamed TenantID → TenantId. Committed as a1b2c3d;
  will be included in the next push.`
- Negative match (do NOT treat as committed — nothing was committed, so there is no SHA
  to check): `**[AI]** Fixed: <summary>. Diff staged locally, awaiting your commit.` —
  the `no-commit` reply template.

A commit SHA is extracted from the matched reply text when the phrasing resolves to one
cleanly (e.g. "Committed as `<sha>`", "commit `<sha>`" — no exact template match required).

**`openFindingsMarker` — a second, independent marker-phrase match, checked on the same reply.**
A `deep-fix` run that ends `stop-max-rounds` (SKILL.md Phase 4's "Deep-fix dispatch — brief and
outcomes") still posts an affirmative commit claim — the fix IS committed — but must NOT be
treated as `cured` by a later cycle's catch-up branch, because open review findings remain. Rather
than inventing a new `assessedState`, that reply's closing sentence STARTS WITH the marker phrase
`Open findings remain; leaving this thread open`. Match on that phrase as a PREFIX / substring,
punctuation-agnostically: no trailing period is required, and whatever follows it — the
`stop-max-rounds` template's `: <1-2 line list>.`, or a bare `.` — does not affect the match. This
is the same "no exact template match required" stance the commit-claim match above already takes.
Run it independently of that commit-claim match, to set the per-thread `openFindingsMarker` flag
to `true`. A reply with an affirmative commit claim but WITHOUT that phrase has
`openFindingsMarker: false` (the default) — this is the normal `deep-fix` `stop-clean` case and
every non-`deep-fix` `**[AI]**` reply.

This mirrors how `processedCommentIds` above relies on GitHub thread/reply state, not file
persistence, to survive across sessions — the difference is that `processedCommentIds`
dedups already-handled *comments*, while this re-derivation answers a different question
("does this thread already have a committed fix that hasn't been resolved via MCP
yet") straight from GitHub's thread history plus real git ancestry, every cycle, with no
entry of its own to define or maintain.

## Ancestry check — shared git mechanic

Two points in this skill need to confirm whether a commit SHA has landed on some target
ref, and both do it the same way. This section is the canonical description; each call
site (SKILL.md Phase 2 step 5, and Phase 4's "Resolve threads and report" step) references
it instead of restating the commands.

**Shape:**

1. If the target ref is a remote-tracking ref that might be stale, refresh it first:
   `git fetch origin <branch>` — `<branch>` is the bare branch name, never `refs/heads/...`.
2. `git merge-base --is-ancestor <sha> <target-ref>` — exit `0` means `<sha>`'s changes are
   already present on `<target-ref>`; exit `1` means not yet. A SHA that doesn't resolve to a
   known commit in this checkout at all is a distinct failure mode from "not yet an
   ancestor" — a caller reporting the outcome must not conflate the two.

**The two call sites** share this shape but differ in `<target-ref>`, in whether a fresh
`git fetch` is needed, and in what each does with the result:

| Call site | `<target-ref>` | Fetch first? | SHA checked | On success | On failure / inconclusive |
| --- | --- | --- | --- | --- | --- |
| SKILL.md Phase 2 step 5 (start of every cycle) | `origin/<headRefName>` | Yes — `git fetch origin <headRefName>` before checking | SHA extracted from the thread's existing affirmative commit-claim reply (`claimedSha`) | `assessedState: cured` — call `pull_request_review_write` `resolve_thread` with the thread's node ID and report it resolved (see Phase 4) — UNLESS the thread's `openFindingsMarker` is `true`, in which case do NOT resolve; report `T#<id> cured (open findings) — left open` instead | `assessedState: unconfirmed-commit-claim` — surface to the human and wait; no `autonomous` bypass |
| SKILL.md Phase 4 "Resolve threads and report" (post-push confirmation) | `<pushed-tip>` — the just-pushed commit/branch state THIS cycle's own push produced, NOT the remote-tracking ref | No — the push that just happened is the freshest possible state | The SHA of the commit made this cycle for that thread (or, for a thread carried over from Phase 2 step 5's `unconfirmed-commit-claim` outcome, the `claimedSha` flagged earlier this cycle) | Call `resolve_thread` and report the thread resolved | Report the thread as still open; do not guess |

`claimedSha` / `shaResolvesLocally` / `isAncestorOfRemote` are how Phase 2 step 5's result
travels forward to Phase 4 within the same cycle, so the "Resolve threads and report" step
doesn't need to re-derive them from scratch for a carried-over thread — it re-runs the check
itself against the new target ref rather than trusting the cached values.

## PR metadata (resolved once, reused every cycle)

Cached from Phase 1 bootstrap:

```json
{
  "owner": "Vasar007",
  "repo": "my-repo",
  "pullRequestNumber": 42,
  "title": "<PR title>",
  "headRefName": "feature/my-branch",
  "baseRefName": "main",
  "state": "open",
  "html_url": "https://github.com/Vasar007/my-repo/pull/42"
}
```

Re-fetch on each cycle only if the previous cycle observed a state change (PR merged, closed, etc.). Otherwise reuse.

## Cycle log — user-facing

Printed after every cycle. Keeps the user informed without overwhelming the chat.

Format:

```text
Cycle <N> @ <HH:MM> — PR #<number> (<threads-checked> threads, <new-comments> new comments)
  T#<commentId> [<Tag>] <file>:<line> → <short outcome> | <reply status>
  T#<commentId> [<Tag>] <file>:<line> → <short outcome> | <reply status>
  ...

Skipped (already processed this session): <count>
Skipped (no tag match for tags=<filter>): <count>
Next cycle in <interval> (via /loop).
```

### `<short outcome>` values

| Outcome                            | When                                                     |
|------------------------------------|----------------------------------------------------------|
| `fixed (<N> LoC)`                  | Small-fix path completed.                                |
| `drafted`                          | Medium/large diff drafted in chat, waiting for approval. |
| `answer drafted`                   | `[Question]` answer drafted and posted as `[AI][Draft]`. |
| `discussion flagged`               | `[ToDiscuss]` surfaced to user, no reply.                |
| `verdict: <enum>`                  | AutoReview branch; include verdict + confidence.         |
| `tracked #<id>`                    | `[OutOfScope]` issue created.                            |
| `noted`                            | `[Note]` or untagged; summarized in chat.                |
| `pattern flagged`                  | `[Repetition]` surfaced with occurrence count.           |
| `stalemate — escalation suggested` | >3 back-and-forth replies detected.                      |
| `skipped — cannot read file`       | File missing or moved.                                   |
| `error — <short reason>`           | Transient failure; will retry next cycle.                |
| `deep-fix (<N> rounds, clean)`     | `deep-fix` thread; review loop ended `stop-clean`.        |
| `deep-fix — open findings`         | `deep-fix` thread; review loop ended `stop-max-rounds`; thread left open (`openFindingsMarker: true`). |
| `deep-fix — blocked`               | `deep-fix` thread; review loop ended `stop-blocked` (build red); this cycle's push is cancelled. |

### `<reply status>` values

- `reply posted` — `[AI]` reply sent successfully.
- `draft posted` — `[AI][Draft]` reply sent, awaiting human confirmation.
- `no reply (dry-run)` / `no reply (no-reply)` — per parameter flag.
- `no reply (awaiting approval)` — action not taken because it requires human approval.
- `reply failed — <short reason>` — MCP error; will retry next cycle.
- `resolved (this cycle's push landed it)` — the fix is committed, replied to, pushed, AND the thread has been resolved via `pull_request_review_write` `resolve_thread` (see SKILL.md Phase 4).
- `reply posted, pending push` — reply is live, but not yet resolved because the commit hasn't been pushed this cycle.
- `pushed, resolve failed — <short reason>` — the commit is pushed and confirmed on the remote, but the `resolve_thread` call itself errored; resolve manually via the GitHub UI. A later cycle's Phase 2 step 5 will keep retrying.

## Examples

### Typical polling cycle

```text
Cycle 2 @ 15:57 — PR #42 (8 threads, 3 new comments)
  T#12 [ToFix]       Auth.cs:42               → fixed (2 LoC)               | reply posted
  T#17 [AutoReview]  Domain/User.cs:88        → verdict: false-positive     | draft posted
  T#22 [OutOfScope]  Sessions/Repo.cs:120     → tracked #876                | reply posted

Skipped (already processed this session): 5
Skipped (no tag match for tags=ToFix,AutoReview): 0
Next cycle in 15m (via /loop).
```

### Carried-over thread, resolved

```text
Cycle 2 @ 15:42 — PR #4421 (5 threads checked, 2 new comments)
  T#9  [ToFix]  Retry.cs:17          → fixed (cycle 1), commit 9f3a1c2       | resolved (this cycle's push landed it)
  T#12 [ToFix]  Auth.cs:42           → fixed (2 LoC), commit a1b2c3d        | reply posted, pending push

1 commit ready, not yet pushed — push when ready.
```

`T#9`'s fix was committed and replied to back in cycle 1, but that cycle ended before its
push happened. At the start of cycle 2, Phase 2 step 5 re-read the existing
`**[AI]** Fixed: ... Committed as 9f3a1c2` reply, found it was not yet an ancestor of
`origin/<headRefName>`, and flagged it `unconfirmed-commit-claim`. Cycle 2's push happened
to include `9f3a1c2`, so once that push landed, Phase 4's "Resolve threads and report" step
re-ran the ancestry check against `<pushed-tip>`, called `resolve_thread`, and reported
`T#9` resolved — in the SAME cycle the push landed, not a cycle later. Because the resolve
call flips `T#9`'s `isResolved` to `true` on GitHub itself, Phase 2's pre-filter skips it on
every later fetch; it will not appear in cycle 3's table at all.

### Dry-run cycle

```text
Cycle 1 @ 09:03 — PR #42 (8 threads, 8 new comments) [dry-run]
  T#12 [ToFix]       Auth.cs:42               → would fix (2 LoC)           | no reply (dry-run)
  T#17 [AutoReview]  Domain/User.cs:88        → verdict: false-positive     | no reply (dry-run)
  T#22 [OutOfScope]  Sessions/Repo.cs:120     → would track as issue        | no reply (dry-run)
  T#24 [Note]        README.md:3              → noted                       | no reply (dry-run)
  ...

Skipped (already processed this session): 0
Next cycle in 15m (via /loop). Re-run without `dry-run` to act.
```

### Stalemate detection

```text
Cycle 4 @ 16:12 — PR #42 (8 threads, 1 new comment)
  T#17 [AutoReview]  Domain/User.cs:88        → stalemate — escalation suggested | no reply (awaiting approval)

Skipped (already processed this session): 7
Next cycle in 15m (via /loop). Thread T#17 has 4 exchanges; consider talking it out.
```

## Session lifecycle

- Start of session (first `/loop` tick or first one-shot run): empty `processedCommentIds`, empty PR metadata. Run Phase 1 bootstrap, then Phase 2–5.
- Mid-session (subsequent `/loop` ticks): reuse `processedCommentIds` and PR metadata. Skip Phase 1 except for a PR-status recheck.
- End of session: the user stops `/loop`, or the PR transitions to `merged` / `closed`. On PR completion, print a final summary and stop. Do NOT persist state across sessions.
