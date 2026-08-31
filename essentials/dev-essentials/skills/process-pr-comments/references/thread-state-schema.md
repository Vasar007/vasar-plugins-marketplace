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
A `deep-fix` run that ends `stop-max-rounds` (SKILL.md Phase 4's "Stage 3 — `deep-fix` brief and
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

Three points in this skill need to confirm whether a commit SHA has landed on some target
ref, and all three do it the same way. This section is the canonical description; each call
site (SKILL.md Phase 2 step 5, the Stage 2 pre-mutation re-verification, and Phase 4's
"Resolve threads and report" step) references it instead of restating the commands.

**Shape:**

1. If the target ref is a remote-tracking ref that might be stale, refresh it first:
   `git fetch origin <branch>` — `<branch>` is the bare branch name, never `refs/heads/...`.
2. `git merge-base --is-ancestor <sha> <target-ref>` — exit `0` means `<sha>`'s changes are
   already present on `<target-ref>`; exit `1` means not yet. A SHA that doesn't resolve to a
   known commit in this checkout at all is a distinct failure mode from "not yet an
   ancestor" — a caller reporting the outcome must not conflate the two.

**The three call sites** share this shape but differ in `<target-ref>`, in whether a fresh
`git fetch` is needed, and — most importantly — in what each does with the result:

| Call site | `<target-ref>` | Fetch first? | SHA checked | On success | On failure / inconclusive |
| --- | --- | --- | --- | --- | --- |
| SKILL.md Phase 2 step 5 (initial classification, Stage 1) | `origin/<headRefName>` | Yes — `git fetch origin <headRefName>` before checking | SHA extracted from the thread's existing affirmative commit-claim reply (becomes `claimedSha`) | Derive `assessedState: cured`; default action resolves the thread now as a catch-up step before this cycle's own Phase 3/4 run (the `cured` verdict Stage 1 derives; the actual resolve is performed by Stage 2 after its own re-verification — see row 2) — UNLESS the thread's `openFindingsMarker` is `true` (see § "Stage 1 report"), in which case skip the catch-up resolve and report `T#<id> cured (open findings) — left open` instead | Derive `assessedState: unconfirmed-commit-claim`; surface to the human and wait — no `autonomous` bypass |
| Stage 2 pre-mutation re-verification (SKILL.md § "Dispatch model") | `origin/<headRefName>` | No — Stage 1 already fetched it this cycle | The report's `claimedSha` field for that thread | Proceed with the `cured` catch-up resolve, as Stage 2's first action, before Phase 3 — UNLESS the thread's `openFindingsMarker` is `true`, in which case skip the catch-up resolve and report `T#<id> cured (open findings) — left open` instead | Do NOT resolve; fall through to `unconfirmed-commit-claim` handling instead |
| SKILL.md Phase 4 "Resolve threads and report" (post-push confirmation) | `<pushed-tip>` — the just-pushed commit/branch state THIS cycle's own push produced, NOT the remote-tracking ref | No — the push that just happened is the freshest possible state | The SHA of the commit made this cycle for that thread (or, for a carried-over thread, the `claimedSha` Phase 2 step 5 flagged earlier this cycle) | Call `resolve_thread` and report the thread resolved (for a carried-over thread, only if the human also answered Phase 2 step 5's prompt this session with a push-and-resolve direction for that thread — see SKILL.md Phase 4) | Report the thread as still open; do not guess |

`claimedSha` / `shaResolvesLocally` / `isAncestorOfRemote` (see the Stage 1 report's
per-thread entry fields below) are how Stage 1's Phase 2 step 5 result travels forward —
to Stage 2's pre-mutation re-verification, and within the same cycle to Phase 4's "Resolve
threads and report" step for a carried-over thread — so neither downstream call site has to
re-derive them from scratch; each re-runs the check itself against its own target ref rather
than trusting the cached values.

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

## Stage 1 report — the Phase 2 → Phase 3 handoff

The contract between the two dispatches described in SKILL.md § "Dispatch model — two stages by default, two models". Stage 1 (Haiku, Phases 1–2) returns exactly this; Stage 2 (Sonnet, Phases 3–5) treats it as its ONLY source of thread data and does not re-issue `pull_request_read` `method: get_review_comments`. Every field exists so that Stage 2 never has to re-read a raw GitHub review-comment payload to act.

Not persisted, not cached across cycles: each cycle of a `/loop` run re-runs Stage 1 from scratch, because thread state changes between cycles (new reviewer replies, a push landing an earlier SHA). This is the same no-persisted-state stance as § "Committed-fix detection" above.

### Envelope

```json
{
  "cycleNumber": 1,
  "prMetadata": { "…": "the § PR metadata block above, verbatim — Stage 1 resolved it in Phase 1 and its own cache dies with the dispatch" },
  "summary": {
    "threadsFetched": 47,
    "systemNoiseDropped": 39,
    "activeThreads": 8,
    "newComments": 2,
    "byTag": { "ToFix": 3, "AutoReview": 2, "Question": 1, "OutOfScope": 1, "Note": 1 },
    "byAssessedState": { "fresh-unhandled": 5, "cured": 1, "unconfirmed-commit-claim": 1, "already-assessed": 1 },
    "needsStage2Action": 5,
    "skippedNoTagMatch": 0,
    "newerHumanReplyFlagged": 1
  },
  "threads": [ "one entry per active thread — shape below" ],
  "blockers": []
}
```

`summary` exists so the orchestrating session can report cycle counts to the user immediately, without waiting for Stage 2. `summary.systemNoiseDropped` counts the threads Phase 2 dropped before classifying — bot-authored noise (Phase 2 step 1) plus threads GitHub already marks `isResolved` / `isOutdated` (Phase 2 step 2). `summary.newComments` is the count of comments seen this cycle that are not already in `processedCommentIds` — Stage 1 has every input needed to count this directly, which feeds the cycle-log header's "N new comments" figure (SKILL.md Phase 5) without Stage 2 having to re-derive it from the per-thread `comments` arrays. `blockers` is a list of free-text STOP conditions Stage 1 hit and could not resolve on its own (`owner`/`repo` not supplied and not parseable from a URL, the target PR not found, MCP unavailable) — a one-shot unnamed subagent cannot ask the user, so it reports and the orchestrator asks. A non-empty `blockers` with an empty `threads` means Stage 2 is NOT dispatched this cycle.

### Per-thread entry

```json
{
  "commentId": 92,
  "threadNodeId": "PRRT_kwDO…",
  "htmlUrl": "https://github.com/Vasar007/my-repo/pull/42#discussion_r92",
  "isResolved": false,
  "isOutdated": false,
  "filePath": "<repo-relative/path>/Auth.cs",
  "lineStart": 42,
  "lineEnd": 42,
  "tags": ["ToFix"],
  "isAutomatedReview": false,
  "comments": [
    {
      "commentId": 92,
      "author": "<Reviewer Display Name>",
      "isAiAuthored": false,
      "text": "**[ToFix]** Rename FooID to FooId — matches the rest of this file."
    }
  ],
  "assessedState": "fresh-unhandled",
  "claimedSha": null,
  "shaResolvesLocally": null,
  "isAncestorOfRemote": null,
  "newerHumanReply": false,
  "newerHumanReplyCommentId": null,
  "overrideCandidates": [],
  "aiReviewerExchangeCount": 0,
  "sameTextAsThreads": [],
  "openFindingsMarker": false
}
```

### Fields

| Field                                          | Required | Notes                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `commentId` / `threadNodeId`                    | yes      | The top comment's ID (used for the `T#` tag and cross-thread references) and the thread's node ID (required by `pull_request_review_write` `method: resolve_thread`). Distinct — never interchange them.                                                                                                                                                                                                        |
| `htmlUrl`                                       | yes      | The `html_url` returned by `pull_request_read` for the thread's top comment, carried verbatim. Stage 2 uses it for the T# link and for cross-thread references — SKILL.md Phase 4 forbids hand-building URLs.                                                                                                                                                                                                   |
| `isResolved` / `isOutdated`                     | yes      | GitHub's own thread-state booleans from Phase 2 step 2. A surviving roster entry has both `false` (unless `include-resolved` is set).                                                                                                                                                                                                                                                                          |
| `filePath` / `lineStart` / `lineEnd`           | yes      | The thread's file path + line range (Phase 2 step 3). `null` for threads with no file context (e.g. PR-level automated-review summary banners).                                                                                                                                                                                                                                                                |
| `tags`                                         | yes      | Parsed leading bracket tags in order, without brackets — e.g. `["ToFix","Performance"]`. `["Note"]` when nothing parses (Phase 2 step 4's untagged rule).                                                                                                                                                                                                                                                      |
| `isAutomatedReview`                             | yes      | `true` when the comment carries an automated-review header or first-line marker. Routes Stage 2 to Phase 3b, which takes precedence over `tags`.                                                                                                                                                                                                                                                               |
| `comments`                                     | yes      | The full chain, oldest first, with **verbatim `text`** — not a summary. Exact reviewer wording is load-bearing for `[ToFix]`/`[Question]`/`[ToDiscuss]` replies and for Stage 2's judgement calls, and it is the one field that cannot be recovered without a re-fetch. `isAiAuthored` uses the `**[AI]**` / legacy `[AI]` prefix test only, never comment author identity (Phase 2 step 4).                       |
| `assessedState`                                | yes      | Phase 2 step 5's outcome, one of `fresh-unhandled` / `cured` / `unconfirmed-commit-claim` / `already-assessed`. See the mapping below.                                                                                                                                                                                                                                                                         |
| `claimedSha`                                   | when any | SHA extracted from the affirmative commit claim, or `null` when the reply claimed a commit without a cleanly extractable SHA.                                                                                                                                                                                                                                                                                  |
| `shaResolvesLocally` / `isAncestorOfRemote`    | when any | Raw results of Stage 1's `git fetch origin <headRefName>` + `git merge-base --is-ancestor <sha> origin/<headRefName>`. Kept alongside `assessedState` so Stage 2 can render Phase 2 step 5's exact report wording (`hasn't landed on the remote yet` vs. `this checkout can't resolve the SHA locally` vs. `no SHA could be extracted`) without re-running git.                                                     |
| `newerHumanReply` / `newerHumanReplyCommentId` | yes      | Phase 2 step 5's guard: a non-AI-authored reply landed after the newest AI reply. `true` means Stage 2 runs NO catch-up branch on this thread and instead classifies that newest human reply as if no prior AI commit-claim existed.                                                                                                                                                                             |
| `overrideCandidates`                           | yes      | Candidate per-thread reviewer overrides Stage 1 spotted by plain phrase matching — `[{ "commentId": 94, "phrase": "just fix it", "direction": "fix-directly" }]`, `direction` being `fix-directly` or `draft-first`. **Candidates only.** Stage 1 does the cheap substring match; Stage 2 decides whether the override genuinely applies and whether the reviewer's intent is unambiguous (SKILL.md Phase 3). Empty array, never omitted. |
| `aiReviewerExchangeCount`                       | yes      | Count of `**[AI]**`-prefixed replies paired with reviewer responses that followed them, across the thread's full GitHub history (SKILL.md § Stalemate detection). Counting is mechanical and belongs to Stage 1; judging whether the latest two show unresolved disagreement is Stage 2's.                                                                                                                        |
| `sameTextAsThreads`                             | optional | Other thread IDs in this cycle whose reviewer comment text is identical or near-identical. Feeds Phase 4's "bundle threads that share one pattern" rule and the `[Repetition]` matrix entry. Empty array when none.                                                                                                                                                                                             |
| `openFindingsMarker`                           | yes      | `true` when this thread's newest affirmative-commit-claim reply has a closing sentence STARTING WITH the marker phrase `Open findings remain; leaving this thread open` (prefix match, punctuation-agnostic — see § "Committed-fix detection"; a `deep-fix` run that ended `stop-max-rounds`). `false` (default) for every other thread, including a `deep-fix` run that ended `stop-clean`. Gates the `cured` catch-up resolve — see the mapping below and the Ancestry check table's rows 1–2. |

### `assessedState` mapping to Phase 2 step 5

Stage 1 derives these using step 5's logic exactly as written in SKILL.md — this table is a name for each of its outcomes, not a restatement of the logic:

| `assessedState`            | Step 5 outcome                                                                                                                     | What Stage 2 does                                                                                                                                                                                                                                                                                                           |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fresh-unhandled`          | No `**[AI]**` / `**[AI][Draft]**` reply exists at all.                                                                             | Normal Phase 3 classification.                                                                                                                                                                                                                                                                                            |
| `cured`                    | Affirmative commit claim whose SHA is already an ancestor of `origin/<headRefName>`.                                               | Re-verify via the ancestry check (see § "Ancestry check", row 2) before performing the catch-up resolve as Stage 2's first action; fall through to `unconfirmed-commit-claim` on disagreement. Skip the catch-up resolve when `openFindingsMarker` is `true`, reporting `T#<id> cured (open findings) — left open` instead. |
| `unconfirmed-commit-claim` | Step 5's merged branch: not yet an ancestor, OR the SHA doesn't resolve in this checkout, OR no SHA cleanly extracted.             | Surface step 5's prompt and wait. No `autonomous` bypass. Nothing implemented on this thread.                                                                                                                                                                                                                              |
| `already-assessed`         | Newest AI reply is terminal but claims no commit (`**[AI][Draft]**`, `Tracked as issue #<id>`, a `[Note]` acknowledgement, …).      | Leave alone unless `newerHumanReply` is `true`.                                                                                                                                                                                                                                                                            |

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
`origin/<headRefName>`, and flagged it `unconfirmed-commit-claim`, surfacing the prompt to
the human — who answered this session with a push-and-resolve direction for `T#9`. Cycle 2's
push happened to include `9f3a1c2`, so once that push landed, Phase 4's "Resolve threads and
report" step re-ran the ancestry check against `<pushed-tip>` and — the human having
authorized it — called `resolve_thread`, and reported `T#9` resolved — in the SAME cycle the
push landed, not a cycle later. Because the resolve call flips `T#9`'s `isResolved` to `true`
on GitHub itself, Phase 2's pre-filter skips it on every later fetch; it will not appear in
cycle 3's table at all.

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
