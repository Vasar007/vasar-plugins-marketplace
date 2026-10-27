# Committed-fix state (Phase 2 step 5)

Stage 1 runs this step for each thread of the active roster, in every cycle. No state persists between cycles. The step reads the thread history that Phase 2 already fetched, and real git ancestry. The text-match rules for a commit claim and for `openFindingsMarker` are in `thread-state-schema.md` § "Committed-fix detection".

## Outcomes

Find the newest reply of Claude in the thread: a reply that starts with `**[AI]**` or `**[AI][Draft]**`, in the bold form or in the old plain form. A reply with the phrase `Committed as <sha>` or `commit <sha>` next to the fix summary is an **affirmative commit claim**. The `no-commit` reply (`Diff staged locally, awaiting your commit.`) is not a commit claim. It reports an edit, but no commit.

- **`fresh-unhandled`**: no `**[AI]**` or `**[AI][Draft]**` reply exists. Go on to Phase 3.
- **`already-assessed`**: the newest such reply is not an affirmative commit claim. Examples: a `**[AI][Draft]**` reply, `Tracked as issue #<id>`, a `[Note]` or out-of-scope acknowledgement, or another reply that claims no commit. Leave the thread alone. One exception: a newer reply of a human or a reviewer exists after it. Then classify that newest human reply in Phase 3. Treat it like a thread with no earlier AI reply.
- **`cured`**: an affirmative commit claim exists, and its SHA is already an ancestor of the remote branch. Resolve the thread, unless `openFindingsMarker` is `true`, and report it as resolved.
- **`unconfirmed-commit-claim`**: an affirmative commit claim exists, but nothing shows yet that it is safe to report as ready.

## Guard: a newer reply of a human

Run this guard first, before you derive `cured` or `unconfirmed-commit-claim`. Look for a reply after the newest commit-claim reply of Claude that is not a reply of Claude. Such a reply does not start with `**[AI]**`, `**[AI][Draft]**`, or the old plain form, so it comes from a human or a reviewer.

If such a reply exists, run no catch-up branch on this thread, whatever the SHA and the ancestry check show. Report: `T#<id> has a newer reply after the AI's last comment — needs human attention before any automated catch-up action.` Then classify that newest human reply in Phase 3. If no such reply exists, go on with the steps below.

## SHA and ancestry check

1. If the wording of the reply gives a commit SHA clearly, take it. Examples: `Committed as <sha>`, `commit <sha>`. An exact template match is not required.
2. Run the ancestry check (`thread-state-schema.md` § "Ancestry check") for that SHA against `origin/pull/<prId>/head`. This ref holds the head of the PR, also for a PR from a fork. The command list of that section shows how to fetch it.

## Report modes

These rules apply to the two outcomes below:

- With neither `dry-run` nor `no-reply`, take the default action of the outcome.
- With `no-reply`, ask the user no question. Print the report line of the outcome, and the human handles the thread.
- With `dry-run`, print the same report line, with no question.

## `cured`

The SHA resolves locally and is an ancestor of `origin/pull/<prId>/head`. The fix already landed on the remote through the push of an earlier cycle or invocation, but the resolve call is missing or failed. This is the catch-up path. Normally, the `is_resolved` filter of Phase 2 drops a resolved thread before this step. Always derive this state.

- If `openFindingsMarker` is `true` for the thread (see `thread-state-schema.md`), do not resolve it. Report `T#<id> cured (open findings) — left open.`
- Else call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` and `threadId: <threadNodeId>` from the roster. Also pass `owner`, `repo`, and `pullNumber` from Phase 1. The schema of the tool requires all three on every call, although `resolve_thread` does not use their values. A resolve of an already resolved thread does nothing, so an old roster entry does no harm.
- On success, report: `T#<id> resolved — <file>:<line>, commit <sha>.`
- On an MCP error, report: `T#<id> cured — <file>:<line>, commit <sha> — resolve failed (<short reason>), resolve manually via GitHub UI.`

Stage 1 only derives `cured`. Stage 2 makes the resolve call after its own ancestry check (see "Dispatch model" in `SKILL.md`).

## `unconfirmed-commit-claim`

This outcome covers three cases:

- The SHA resolves locally, but it is not yet an ancestor of the remote.
- The SHA does not resolve to a known commit in this checkout.
- The reply claims a commit, but no SHA comes out of it clearly.

In each case, nothing shows yet that the commit claim is safe to report as ready.

- Do not treat the thread as fresh or unhandled, and do not implement anything new on it.
- No flag skips this outcome, also not `autonomous`. An unconfirmed SHA needs the input of a human.
- Report: `T#<id> already has an AI reply about a committed fix (commit <sha-or-"unspecified">) that can't be confirmed safe to report as ready — <hasn't landed on the remote yet | this checkout can't resolve the SHA locally | no SHA could be extracted from the reply>.`
- Leave the thread as it is until the user answers. The orchestrating session asks the question (see "Dispatch model" in `SKILL.md`). Phase 4 uses the answer (see `commit-push-resolve.md`).
