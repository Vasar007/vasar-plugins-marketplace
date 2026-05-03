# Thread State Schema

In-session state the `process-pr-comments` skill keeps to avoid reprocessing comments across polling cycles, and the cycle-log format printed to the user. State is session-local — a fresh `/loop` session starts empty and relies on ADO thread state (reply text, thread status) to detect previously-handled comments.

## `processedCommentIds` — dedup set

A plain set of ADO comment IDs that have been fully handled this session.

Entry shape (logical; implementation is whatever is ergonomic for Claude in the turn):

```json
{
  "pullRequestId": 4421,
  "threadId": 17,
  "commentId": 92,
  "tag": "ToFix",
  "action": "fixed",
  "verdict": null,
  "confidence": null,
  "replyPosted": true,
  "replyCommentId": 93,
  "editedFiles": ["<repo-relative/path>/Auth.cs"],
  "workItemId": null,
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

| Field                    | Required | Notes                                                                                                                                                                                                                                                   |
|--------------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `pullRequestId`          | yes      | Sanity check in case the user re-invokes with a different PR mid-session (the skill stops and asks rather than mixing state).                                                                                                                           |
| `threadId` / `commentId` | yes      | ADO identifiers returned by `repo_list_pull_request_thread_comments`.                                                                                                                                                                                   |
| `tag`                    | yes      | The primary tag applied (or `AIR` / `Note`).                                                                                                                                                                                                            |
| `action`                 | yes      | One of `fixed`, `drafted`, `noted`, `tracked`, `skipped`. `skipped` is written only for explicit terminal skips (e.g., `threadContext` file missing/moved, user answered "skip" on a `[Question]` confirm prompt) — never for `tags`-filter exclusions. |
| `verdict`                | AIR only | One of the five AIR verdicts.                                                                                                                                                                                                                           |
| `confidence`             | AIR only | `high` / `medium` / `low`.                                                                                                                                                                                                                              |
| `replyPosted`            | yes      | `false` when `dry-run` / `no-reply` is on.                                                                                                                                                                                                              |
| `replyCommentId`         | optional | ID returned by `repo_reply_to_comment` — useful for user reference.                                                                                                                                                                                     |
| `editedFiles`            | optional | List of files touched by this action. Empty for drafts/notes.                                                                                                                                                                                           |
| `workItemId`             | optional | Set when `[OutOfScope]` tracking produced a work item.                                                                                                                                                                                                  |
| `cycleNumber`            | yes      | Starts at 1, increments each cycle.                                                                                                                                                                                                                     |
| `timestamp`              | yes      | ISO 8601 UTC when the action completed.                                                                                                                                                                                                                 |

## PR metadata (resolved once, reused every cycle)

Cached from Phase 1 bootstrap:

```json
{
  "organization": "<collection>",
  "project": "<Project>",
  "repoId": "c1...",
  "repoName": "<Repo>",
  "pullRequestId": 4421,
  "title": "#<workitem> <title>",
  "sourceRefName": "refs/heads/<source-branch>",
  "targetRefName": "refs/heads/<target-branch>",
  "status": "active",
  "url": "https://<your-ado-host>/<collection>/<Project>/_git/<Repo>/pullrequest/4421"
}
```

Re-fetch on each cycle only if the previous cycle observed a state change (PR completed, abandoned, etc.). Otherwise reuse.

## Cycle log — user-facing

Printed after every cycle. Keeps the user informed without overwhelming the chat.

Format:

```text
Cycle <N> @ <HH:MM> — PR <id> (<threads-checked> threads, <new-comments> new comments)
  T#<threadId> [<Tag>] <file>:<line> → <short outcome> | <reply status>
  T#<threadId> [<Tag>] <file>:<line> → <short outcome> | <reply status>
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
| `verdict: <enum>`                  | AIR branch; include verdict + confidence.                |
| `tracked #<id>`                    | `[OutOfScope]` work item created.                        |
| `noted`                            | `[Note]` or untagged; summarized in chat.                |
| `pattern flagged`                  | `[Repetition]` surfaced with occurrence count.           |
| `stalemate — escalation suggested` | >3 back-and-forth replies detected.                      |
| `skipped — cannot read file`       | `threadContext` file missing or moved.                   |
| `error — <short reason>`           | Transient failure; will retry next cycle.                |

### `<reply status>` values

- `reply posted` — `[AI]` reply sent successfully.
- `draft posted` — `[AI][Draft]` reply sent, awaiting human confirmation.
- `no reply (dry-run)` / `no reply (no-reply)` — per parameter flag.
- `no reply (awaiting approval)` — action not taken because it requires human approval.
- `reply failed — <short reason>` — MCP error; will retry next cycle.

## Examples

### Typical polling cycle

```text
Cycle 2 @ 15:57 — PR 4421 (8 threads, 3 new comments)
  T#12 [ToFix]       Auth.cs:42               → fixed (2 LoC)               | reply posted
  T#17 [AIR]         Domain/User.cs:88        → verdict: false-positive     | draft posted
  T#22 [OutOfScope]  Sessions/Repo.cs:120     → tracked #876543             | reply posted

Skipped (already processed this session): 5
Skipped (no tag match for tags=ToFix,AIR): 0
Next cycle in 15m (via /loop).
```

### Dry-run cycle

```text
Cycle 1 @ 09:03 — PR 4421 (8 threads, 8 new comments) [dry-run]
  T#12 [ToFix]       Auth.cs:42               → would fix (2 LoC)           | no reply (dry-run)
  T#17 [AIR]         Domain/User.cs:88        → verdict: false-positive     | no reply (dry-run)
  T#22 [OutOfScope]  Sessions/Repo.cs:120     → would track as work item    | no reply (dry-run)
  T#24 [Note]        README.md:3              → noted                       | no reply (dry-run)
  ...

Skipped (already processed this session): 0
Next cycle in 15m (via /loop). Re-run without `dry-run` to act.
```

### Stalemate detection

```text
Cycle 4 @ 16:12 — PR 4421 (8 threads, 1 new comment)
  T#17 [AIR]         Domain/User.cs:88        → stalemate — escalation suggested | no reply (awaiting approval)

Skipped (already processed this session): 7
Next cycle in 15m (via /loop). Thread T#17 has 4 exchanges; consider talking it out.
```

## Session lifecycle

- Start of session (first `/loop` tick or first one-shot run): empty `processedCommentIds`, empty PR metadata. Run Phase 1 bootstrap, then Phase 2–5.
- Mid-session (subsequent `/loop` ticks): reuse `processedCommentIds` and PR metadata. Skip Phase 1 except for a PR-status recheck.
- End of session: the user stops `/loop`, or the PR transitions to `completed` / `abandoned`. On PR completion, print a final summary and stop. Do NOT persist state across sessions.
