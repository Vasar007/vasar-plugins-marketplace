# Thread State Schema

This file has the state that `process-pr-comments` keeps in the session, so that a polling cycle does not process a comment again. It also has the format of the cycle log for the user. The state lives only in the session. A new `/loop` session starts empty. It finds the comments that an earlier session handled from the thread state on GitHub: the reply text and the state of the thread.

## Contents

- `processedCommentIds`: dedup set
- Committed-fix detection: re-derived every cycle, not persisted
- Ancestry check: shared git mechanic
- PR metadata (resolved once, reused every cycle)
- Stage 1 report: the Phase 2 → Phase 3 handoff
- Cycle log: user-facing
- Examples
- Session lifecycle

## `processedCommentIds` — dedup set

A set with one entry for each GitHub comment that this session fully handled.

The entry shape below is logical. Keep it in any form that works in the turn.

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

- Add an entry only after the action of the comment, or an explicit decision to skip it, completed without error.
- After a temporary failure (an MCP timeout, a rejected file write), leave the comment unprocessed, so that the next cycle tries again.
- A skip because of the `tags` filter is not an "explicit skip". Do not add the comment to the set. A later invocation with other `tags` must see the comment again.
- A skip of a `[Note]` or untagged comment with no action IS an "explicit skip". Add the comment to the set with `action: "noted"`.

Fields:

| Field | Required | Notes |
| --- | --- | --- |
| `pullRequestNumber` | yes | A safety test. The user can invoke the skill for another PR in the same session. Then the skill stops and asks. It never mixes the state of two PRs. |
| `commentId` | yes | The GitHub comment ID that `pull_request_read` returns. |
| `tag` | yes | The primary tag that the skill applied, or `AutoReview` or `Note`. |
| `action` | yes | One of `fixed`, `drafted`, `noted`, `tracked`, and `skipped`. Write `skipped` only for an explicit final skip, for example the answer `skip` of the user to the approval question of a `[Question]` reply. Never write it for an exclusion by the `tags` filter. |
| `verdict` | AutoReview only | One of the five verdicts of `automated-review-verification.md`. |
| `confidence` | AutoReview only | `high`, `medium`, or `low`. |
| `replyPosted` | yes | `false` with `dry-run` or `no-reply`, and while the reply is pending (`commit-push-resolve.md` § "When replies post"). |
| `replyCommentId` | optional | The ID that `add_reply_to_pull_request_comment` returns, for the user to look up. |
| `editedFiles` | optional | The files that this action touched. Empty for drafts and notes. |
| `issueNumber` | optional | Set after `[OutOfScope]` tracking created a GitHub issue. |
| `cycleNumber` | yes | Starts at 1, and goes up by one in each cycle. |
| `timestamp` | yes | The time in ISO 8601 UTC at which the action completed. |

## Committed-fix detection — re-derived every cycle, not persisted

No stored entry tracks a fix that is committed but not pushed. Phase 2 step 5 finds this state again in every cycle. It reads the thread history on GitHub, the messages of the unpushed local commits, and real git ancestry (`git merge-base --is-ancestor`). The steps, the outcomes, the guard for a newer human reply, and the rules for `dry-run` and `no-reply` are in `committed-fix-state.md`. This section has only the text-match rules that the step uses.

**Affirmative commit claim**. The match is strict, not a loose prefix match. An affirmative commit claim is a reply of Claude with the phrase `Committed as <sha>` or `commit <sha>` next to the fix summary. The reply starts with `**[AI]**`, or with the old plain `[AI]` form. A `**[[T#<id>](<url>)]**` tag between the `**[AI]**` marker and the body is expected, and does not change the match.

- Positive match: `**[AI]** Fixed: renamed TenantID → TenantId. Committed as a1b2c3d; will be included in the next push.`
- Negative match: `**[AI]** Fixed: <summary>. Diff staged locally, awaiting your commit.` This is the `no-commit` reply template. Do not treat it as committed. Nothing was committed, so no SHA exists to test.

**`openFindingsMarker`**. Run a second, separate match on the same reply. A `deep-fix` run that ends `stop-max-rounds` still posts an affirmative commit claim, because the fix is committed (see `deep-fix.md`). But a later cycle must not treat the thread as `cured`, because open review findings remain. The skill uses no new `assessedState` for this case. Instead, the last sentence of that reply STARTS WITH the marker phrase `Open findings remain; leaving this thread open`.

- Match the phrase as a PREFIX or a substring, and ignore the punctuation. The match needs no period after the phrase.
- The text after the phrase does not change the match. It can be the `: <1-2 line list>.` of the `stop-max-rounds` template, or only a `.`.
- Run this match apart from the commit-claim match. On a match, set the `openFindingsMarker` flag of the thread to `true`.
- A reply with an affirmative commit claim but WITHOUT that phrase has `openFindingsMarker: false`, the default. This is the normal case: a `deep-fix` run that ended `stop-clean`, and every `**[AI]**` reply that does not come from `deep-fix`.

## Ancestry check — shared git mechanic

Three steps of the skill test whether a commit SHA is on a target ref. All three use the same commands, and this section is their only description. Each step points here.

The commands:

1. The target ref can be a remote-tracking ref that is stale. Then fetch it first. For the head of the PR, run `git fetch origin "+refs/pull/<prId>/head:refs/remotes/origin/pull/<prId>/head"`. `<prId>` is the PR number. Do not fetch the head branch by its name (`headRefName`). For a PR from a fork, that branch is not on `origin`, but the `pull/<prId>/head` ref is. This fetch needs `origin` to be the base repository of the PR. If the fetch fails, stop, and ask the user which remote holds the base repository. Stage 1 puts this question in the `blockers` list of its report. Then use that remote in place of `origin`.
2. Run `git merge-base --is-ancestor <sha> <target-ref>`. Exit code `0` means that the changes of `<sha>` are already on `<target-ref>`. Exit code `1` means not yet. For a SHA that this checkout does not know at all, git fails with another exit code, for example `128`. That is a different failure from "not yet an ancestor". A step that reports the result must keep the two cases apart.

The three steps use these commands in the same way. They differ in `<target-ref>`, in the need for a new `git fetch`, and most of all in what they do with the result:

| Step | `<target-ref>` | Fetch first? | SHA tested | On success | On failure or an unclear result |
| --- | --- | --- | --- | --- | --- |
| Phase 2 step 5, the first classification (Stage 1, `committed-fix-state.md`) | `origin/pull/<prId>/head` | Yes. Run the fetch of command 1 first. | The SHA from the existing affirmative commit claim of the thread. It becomes `claimedSha`. | Derive `assessedState: cured`. Stage 1 only derives this verdict. By default, Stage 2 makes the catch-up resolve after its own test (row 2), before Phase 3 and Phase 4 of this cycle. If `openFindingsMarker` of the thread is `true`, skip the catch-up resolve. Report `T#<id> cured (open findings) — left open` instead. | Derive `assessedState: unconfirmed-commit-claim`. Show the thread to the human and wait. `autonomous` does not skip this. |
| Stage 2 test before the catch-up resolve (`SKILL.md` § "Dispatch model") | `origin/pull/<prId>/head` | No. Stage 1 already fetched it in this cycle. | The `claimedSha` field of the report for that thread. | Make the `cured` catch-up resolve as the first action of Stage 2, before Phase 3. If `openFindingsMarker` of the thread is `true`, skip the catch-up resolve. Report `T#<id> cured (open findings) — left open` instead. | Do not resolve. Handle the thread as `unconfirmed-commit-claim`. |
| Phase 4 "Resolve threads and report", the test after the push (`commit-push-resolve.md`) | `<pushed-tip>`: the commit or branch state that the push of this cycle produced, not the remote-tracking ref | No. The push of this cycle is the newest state. | The SHA of the commit of this cycle for that thread. For a carried-over thread, the `claimedSha` that Phase 2 step 5 flagged earlier in this cycle. | Call `resolve_thread`, and report the thread as resolved. A carried-over thread also needs a push-and-resolve answer of the human in this session. See group (b) in `commit-push-resolve.md` § "Resolve threads and report". | Report the thread as still open. Do not guess. |

The report fields `claimedSha`, `shaResolvesLocally`, and `isAncestorOfRemote` carry the result of Phase 2 step 5 forward (see § "Stage 1 report"). They go to the test of Stage 2. In the same cycle, they also go to the resolve step of Phase 4 for a carried-over thread. So no later step has to derive them again from the start. But each later step runs the test again against its own target ref, and does not trust the cached values.

## PR metadata (resolved once, reused every cycle)

Phase 1 caches this block:

```json
{
  "owner": "my-org",
  "repo": "my-repo",
  "pullRequestNumber": 42,
  "title": "<PR title>",
  "headRefName": "feature/my-branch",
  "baseRefName": "main",
  "state": "open",
  "html_url": "https://github.com/my-org/my-repo/pull/42"
}
```

Each later cycle runs only the PR-status recheck of Phase 1 (see § "Session lifecycle"). If the state of the PR changed, for example because it was merged or closed, update the cache. Else reuse the cache.

## Stage 1 report — the Phase 2 → Phase 3 handoff

This report is the contract between the two dispatches of `SKILL.md` § "Dispatch model". Stage 1 (Phases 1 and 2) returns exactly this shape. Stage 2 (Phases 3 to 5) uses it as its only source of thread data. Stage 2 does not call `pull_request_read` `method: get_review_comments` again. Each field exists so that Stage 2 never has to read a raw review-comment payload of GitHub to act.

The report is not stored and not cached across cycles. Each cycle of a `/loop` run runs Stage 1 again from the start, because the thread state changes between cycles: new replies of reviewers, or a push that lands an earlier SHA. § "Committed-fix detection" follows the same rule.

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

- `summary` lets the orchestrating session report the cycle counts to the user at once, without a wait for Stage 2.
- `summary.systemNoiseDropped` counts the threads that Phase 2 dropped before the classification. These are the bot comments that Phase 2 step 1 skips, and the threads that GitHub already marks `is_resolved` or `is_outdated` (Phase 2 step 2).
- `summary.newComments` counts the comments of this cycle that are not yet in `processedCommentIds`. Stage 1 has every input that it needs for this count. The number feeds the "N new comments" figure in the header of the cycle log (`SKILL.md` Phase 5). So Stage 2 does not have to derive it from the `comments` arrays of the threads.
- `blockers` lists in free text the stop conditions that Stage 1 met and did not settle on its own. These are: `owner` or `repo` not given and not in a URL, the target PR not found, and MCP not available. A failed fetch of the PR head ref (§ "Ancestry check") is one more. Subagents do not talk to the user. So Stage 1 reports the condition, and the orchestrating session asks.
- If `blockers` is not empty and `threads` is empty, the orchestrating session does not dispatch Stage 2 in this cycle.

### Per-thread entry

```json
{
  "commentId": 92,
  "threadNodeId": "PRRT_kwDO…",
  "htmlUrl": "https://github.com/my-org/my-repo/pull/42#discussion_r92",
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
  "claimSource": null,
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

| Field | Required | Notes |
| --- | --- | --- |
| `commentId` / `threadNodeId` | yes | The ID of the top comment, for the `T#` tag and for references to other threads. The node ID of the thread, which `pull_request_review_write` `method: resolve_thread` requires. The two IDs differ. Never use one in place of the other. |
| `htmlUrl` | yes | The `html_url` that `pull_request_read` returns for the top comment of the thread, word for word. Stage 2 uses it for the T# link and for references to other threads. Never build a URL by hand (`commit-push-resolve.md` § "Reply templates"). |
| `isResolved` / `isOutdated` | yes | The `is_resolved` and `is_outdated` booleans of the thread from Phase 2 step 2. Unless `include-resolved` is set, an entry that stays in the roster has both `false`. |
| `filePath` / `lineStart` / `lineEnd` | yes | The file path and the line range of the thread (Phase 2 step 3). `null` for a thread with no file context, for example the summary banner of an automated review at PR level. |
| `tags` | yes | The parsed leading bracket tags in order, without brackets, for example `["ToFix","Performance"]`. If no tag parses, `["Note"]` (the rule for untagged comments in Phase 2 step 4). |
| `isAutomatedReview` | yes | `true` for a comment with an automated-review header or first-line marker. It sends Stage 2 to Phase 3b, which takes precedence over `tags`. |
| `comments` | yes | The full chain, oldest first, with the **`text` word for word**, not a summary. Stage 2 needs the exact words of the reviewer for `[ToFix]`, `[Question]`, and `[ToDiscuss]` replies and for its judgment calls. Only this field cannot come back without a new fetch. `isAiAuthored` uses only the prefix test (`**[AI]**`, or the old plain `[AI]`), never the identity of the author (Phase 2 step 4). |
| `assessedState` | yes | The outcome of Phase 2 step 5: `fresh-unhandled`, `cured`, `unconfirmed-commit-claim`, or `already-assessed`. See the mapping below. |
| `claimedSha` | when any | The SHA from the affirmative commit claim, or of the newest unpushed local commit that names the thread. `null` for a reply that claims a commit without a clear SHA. |
| `claimSource` | when any | `reply` for a commit claim in an AI reply. `local-commit` for an unpushed local commit that names a thread with no reply about it (`committed-fix-state.md` § "Local commit with no reply"). `null` with no claim. |
| `shaResolvesLocally` / `isAncestorOfRemote` | when any | The raw results of the fetch of the PR head (§ "Ancestry check", command 1) and `git merge-base --is-ancestor <sha> origin/pull/<prId>/head` in Stage 1. They stay next to `assessedState`. So Stage 2 can write the exact report words of Phase 2 step 5 without a new git run: `hasn't landed on the remote yet`, `this checkout can't resolve the SHA locally`, or `no SHA could be extracted`. |
| `newerHumanReply` / `newerHumanReplyCommentId` | yes | The guard of Phase 2 step 5: a reply that is not an AI reply came after the newest AI reply. With `true`, Stage 2 runs no catch-up branch on this thread. It classifies that newest human reply instead. It treats the thread like a thread with no earlier AI commit claim. |
| `overrideCandidates` | yes | Possible overrides of the reviewer for one thread, which Stage 1 found by a plain phrase match: `[{ "commentId": 94, "phrase": "just fix it", "direction": "fix-directly" }]`. `direction` is `fix-directly` or `draft-first`. **Candidates only**. Stage 1 does the cheap substring match. Stage 2 decides whether the override really applies, and whether the intent of the reviewer is clear (`SKILL.md` Phase 3). An empty array, never left out. |
| `aiReviewerExchangeCount` | yes | The count of `**[AI]**` replies with a reply of a reviewer after them. The count covers the full GitHub history of the thread (`SKILL.md` § "Stalemate detection"). Stage 1 makes the count, because it is mechanical. Stage 2 judges whether the last two replies show an open disagreement. |
| `sameTextAsThreads` | optional | Other thread IDs of this cycle with the same or almost the same comment text of the reviewer. They feed the rule for threads with the same note (`commit-push-resolve.md` § "Threads with the same note") and the `[Repetition]` entry of the matrix. With no such threads, an empty array. |
| `openFindingsMarker` | yes | `true` for a thread whose newest affirmative commit claim has a last sentence that STARTS WITH the marker phrase `Open findings remain; leaving this thread open`. This is a prefix match that ignores punctuation (§ "Committed-fix detection"), and the case of a `deep-fix` run that ended `stop-max-rounds`. `false` (the default) for every other thread, also for a `deep-fix` run that ended `stop-clean`. It gates the `cured` catch-up resolve (see the mapping below, and rows 1 and 2 of the table in § "Ancestry check"). |

### `assessedState` mapping to Phase 2 step 5

Stage 1 derives these states with the logic of `committed-fix-state.md`, exactly as written there. This table gives a name to each outcome. It does not repeat the logic.

| `assessedState` | Step 5 outcome | What Stage 2 does |
| --- | --- | --- |
| `fresh-unhandled` | No `**[AI]**` or `**[AI][Draft]**` reply exists, and no unpushed local commit names the thread. | The normal classification of Phase 3. |
| `cured` | An affirmative commit claim whose SHA is already an ancestor of `origin/pull/<prId>/head`. | Run the ancestry check again (§ "Ancestry check", row 2). Then make the catch-up resolve as the first action of Stage 2. If the result disagrees, handle the thread as `unconfirmed-commit-claim`. If `openFindingsMarker` is `true`, skip the catch-up resolve. Report `T#<id> cured (open findings) — left open` instead. |
| `unconfirmed-commit-claim` | The merged case of step 5: not yet an ancestor, or the SHA does not resolve in this checkout, or no clear SHA came out of the reply. Or an unpushed local commit names the thread with no reply about it (`claimSource: local-commit`). | The orchestrating session asks the question of step 5, and the thread waits for the answer. `autonomous` does not skip it. Nothing new is implemented on this thread. |
| `already-assessed` | The newest AI reply is final, but claims no commit (`**[AI][Draft]**`, `Tracked as issue #<id>`, a `[Note]` acknowledgement, and the like). | Leave the thread alone, unless `newerHumanReply` is `true`. |

## Cycle log — user-facing

Print it after every cycle.

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

`SKILL.md` Phase 5 adds more lines: the push state at the end, and the forms for `squash` and `no-commit`.

### `<short outcome>` values

| Outcome | When |
| --- | --- |
| `fixed (<N> LoC)` | The skill implemented the fix: a Small fix, or a larger fix under Bucket A1 or A2. |
| `drafted` | A larger diff is drafted in chat, and waits for approval. |
| `answer drafted` | A `[Question]` answer is drafted and posted as `**[AI][Draft]**`. |
| `discussion flagged` | A `[ToDiscuss]` thread is shown to the user, with no reply. |
| `verdict: <enum>` | The AutoReview path. Add the verdict and the confidence. |
| `tracked #<id>` | An `[OutOfScope]` issue is created. |
| `noted` | A `[Note]` or untagged comment, summed up in chat. |
| `pattern flagged` | A `[Repetition]` thread, shown with the count of occurrences. |
| `stalemate — escalation suggested` | Stalemate detection stopped the automatic replies (see `SKILL.md` § "Stalemate detection"). |
| `skipped — cannot read file` | The file is missing or moved. |
| `error — <short reason>` | A temporary failure. The next cycle tries again. |
| `deep-fix (<N> rounds, clean)` | A `deep-fix` thread whose review loop ended `stop-clean`. |
| `deep-fix — open findings` | A `deep-fix` thread whose review loop ended `stop-max-rounds`. The thread stays open (`openFindingsMarker: true`). |
| `deep-fix — blocked` | A `deep-fix` thread whose review loop ended `stop-blocked` (build red). The push of this cycle is cancelled. |

### `<reply status>` values

- `reply posted`: the `**[AI]**` reply was sent.
- `draft posted`: the `**[AI][Draft]**` reply was sent, and waits for the approval of a human.
- `reply pending`: the `**[AI]**` reply is written and waits for the push (`commit-push-resolve.md` § "When replies post"). The log prints its text.
- `draft pending`: the `**[AI][Draft]**` reply waits in the same way.
- `no reply (dry-run)` or `no reply (no-reply)`: the parameter flag stopped the reply.
- `no reply (awaiting approval)`: the action did not run, because it needs the approval of a human.
- `reply failed — <short reason>`: an MCP error. The next cycle tries again.
- `resolved (this cycle's push landed it)`: the fix is committed, replied to, and pushed, and the skill resolved the thread with `pull_request_review_write` `method: resolve_thread` (see `commit-push-resolve.md`).
- `reply posted, pending push`: the reply posted right before the push, but the push failed. The thread is not resolved yet.
- `pushed, resolve failed — <short reason>`: the commit is pushed and is on the remote, but the `resolve_thread` call failed. Resolve the thread in the GitHub UI. Phase 2 step 5 of each later cycle tries the resolve again.

## Examples

### Typical polling cycle

```text
Cycle 2 @ 15:57 — PR #42 (8 threads, 3 new comments)
  T#12 [ToFix]       Auth.cs:42               → fixed (2 LoC)               | reply pending
  T#17 [AutoReview]  Domain/User.cs:88        → verdict: false-positive     | draft pending
  T#22 [OutOfScope]  Sessions/Repo.cs:120     → tracked #876                | reply posted

1 commit ready, not yet pushed — push when ready.

Skipped (already processed this session): 5
Skipped (no tag match for tags=ToFix,AutoReview): 0
Next cycle in 15m (via /loop).
```

### Carried-over thread, resolved

```text
Cycle 2 @ 15:42 — PR #4421 (5 threads checked, 2 new comments)
  T#9  [ToFix]  Retry.cs:17          → fixed (earlier run), commit 9f3a1c2  | resolved (this cycle's push landed it)
  T#12 [ToFix]  Auth.cs:42           → fixed (2 LoC), commit a1b2c3d        | resolved (this cycle's push landed it)

2 commits pushed as a1b2c3d.
```

The fix of `T#9` was committed in an earlier run, which ended before its go-ahead. So its reply never posted. In cycle 2, Phase 2 step 5 found no AI reply on `T#9`, but the unpushed local commit `9f3a1c2` named it. So the step flagged the thread `unconfirmed-commit-claim` with `claimSource: local-commit`, and the orchestrating session asked the human. The human answered with a push-and-resolve direction for `T#9`. Stage 2 wrote the "Implemented fix" reply from the commit, and posted it with the reply of `T#12` right before the push. The push of cycle 2 carried both commits. The resolve step of Phase 4 then ran the ancestry check again against `<pushed-tip>` and resolved both threads. The resolve call sets `is_resolved` to `true` on GitHub. So the filter of Phase 2 skips both threads in every later fetch.

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

- Start of a session (the first `/loop` tick, or the first one-shot run): `processedCommentIds` and the PR metadata are empty. Run the Phase 1 bootstrap, then Phases 2 to 5.
- Later in the session (each later `/loop` tick): reuse `processedCommentIds` and the PR metadata. Skip Phase 1, except the PR-status recheck: the `pull_request_read` call with `method: get` of Phase 1 step 3.
- End of the session: the user stops `/loop`, or the PR becomes `merged` or `closed`. When the PR is complete, print a final summary and stop. Do not keep the state across sessions.
