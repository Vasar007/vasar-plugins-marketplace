# Committed-fix state (Phase 2 step 5)

Stage 1 runs this step for each thread of the active roster, in every cycle. No state persists between cycles. The step reads the thread history that Phase 2 already fetched, and real git ancestry. It also reads the subject lines of the local commits that the PR head does not have yet (§ "Local commit with no reply"). It reads the subject lines of the commits of the PR too (§ "Commit on the PR head with no reply"). The text-match rules for a commit claim and for `openFindingsMarker` are in `thread-state-schema.md` § "Committed-fix detection".

## Outcomes

Find the newest reply of Claude in the thread: a reply that starts with `**[AI]**` or `**[AI][Draft]**`, in the bold form or in the old plain form. A reply with the phrase `Committed as <sha>` or `commit <sha>` next to the fix summary is an **affirmative commit claim**. The `no-commit` reply (`Diff staged locally, awaiting your commit.`) is not a commit claim. It reports an edit, but no commit.

- **`fresh-unhandled`**: no `**[AI]**` or `**[AI][Draft]**` reply exists, and no commit names the thread: no unpushed local commit, and no commit of the PR. Go on to Phase 3.
- **`already-assessed`**: the newest such reply is not an affirmative commit claim. Examples: a `**[AI][Draft]**` reply, `Tracked as issue #<id>`, a `[Note]` or out-of-scope acknowledgement, or another reply that claims no commit. Leave the thread alone. One exception: a newer reply of a trusted human or reviewer exists after it. Then classify that newest human reply in Phase 3. Treat it like a thread with no earlier AI reply.
- **`cured`**: an affirmative commit claim exists, and its SHA is already an ancestor of the remote branch. Resolve the thread, unless `openFindingsMarker` is `true`, and report it as resolved.
- **`unconfirmed-commit-claim`**: an affirmative commit claim exists, but nothing shows yet that it is safe to report as ready. Or an unpushed local commit names a thread with no reply about it (§ "Local commit with no reply").
- **`pr-commit-no-reply`**: no `**[AI]**` or `**[AI][Draft]**` reply exists, but a commit of the PR names the thread (§ "Commit on the PR head with no reply"). Or the fetch of the base branch failed (step 6 of that section). Print the report line of that section. Ask no question, and do not act on the thread.

## Guard: a newer reply of a human

Run this guard first, before you derive `cured` or `unconfirmed-commit-claim`. Look for a reply after the newest commit-claim reply of Claude that is not a reply of Claude. Such a reply does not start with `**[AI]**`, `**[AI][Draft]**`, or the old plain form, so it comes from a human or a reviewer. Count only a reply of a trusted login (`SKILL.md` Phase 2 step 1). A reply of an untrusted login is not such a reply, and it never goes to Phase 3.

If such a reply exists, run no catch-up branch on this thread, whatever the SHA and the ancestry check show. Report: `T#<id> has a newer reply after the AI's last comment — needs human attention before any automated catch-up action.` Then classify that newest human reply in Phase 3. If no such reply exists, go on with the steps below.

## SHA and ancestry check

1. If the wording of the reply gives a commit SHA clearly, take it. Examples: `Committed as <sha>`, `commit <sha>`. An exact template match is not required.
2. Run the ancestry check (`thread-state-schema.md` § "Ancestry check") for that SHA against `origin/pull/<prId>/head`. This ref holds the head of the PR, also for a PR from a fork. The command list of that section shows how to fetch it.
3. If the SHA resolves locally but is not yet an ancestor of that ref, also run `git merge-base --is-ancestor <sha> HEAD`. Keep the result as `isAncestorOfHead`. Exit code `0` means that the commit is on the local branch, so a push can carry it. Only then is the claim a carried-over claim that can open a push (Rules in `SKILL.md`). Exit code `1` means that the commit is not on the local branch. A SHA that does not resolve, or a reply with no clear SHA, gets `isAncestorOfHead: false`.

## Local commit with no reply

A reply about a fix posts right before the push (`commit-push-resolve.md` § "When replies post"). If a run ended before the go-ahead, the fix has a local commit but no reply. The commit message is then the only record.

1. Once per cycle, after the fetch of `thread-state-schema.md` § "Ancestry check" command 1, run `git log --format='%H %s' origin/pull/<prId>/head..HEAD`. It lists the local commits that the PR head does not have yet, each with its subject line.
2. If the subject line of a commit has `T#<commentId>` with no digit right after it, the commit names that thread. A `T#<commentId>` in the body does not count, because a body can name a thread only as a reference. The subject of Phase 4 step 3 has it. The subject of a commit for several threads has it for each thread (`commit-push-resolve.md` § "Steps for each thread", step 3).
3. Run this test for each thread that goes on to Phase 3: a `fresh-unhandled` thread, and a thread that the guard above sent to Phase 3. If a commit names the thread, derive `unconfirmed-commit-claim` instead. Set `claimSource` to `local-commit` and `claimedSha` to the newest such commit. Set `shaResolvesLocally` and `isAncestorOfHead` to `true`, and `isAncestorOfRemote` to `false`. The `git log` range of step 1 holds only commits of `HEAD` that the PR head does not have. Do not send the thread to Phase 3. A comment in `processedCommentIds` of this session gets no such test. The session still holds its pending reply (Rules in `SKILL.md`).
4. Report: `T#<id> has an unpushed local commit <sha> that names it, but no reply about it — push it and post its reply, or handle it separately?`

With `no-reply`, `no-commit`, or `dry-run`, the report is `T#<id> has an unpushed local commit <sha> that names it, but no reply about it — the human handles it.` and asks no question (§ "Report modes"). A later cycle of a `/loop` session prints the same report.

Phase 4 uses the answer of the human as for a claim in a reply (`commit-push-resolve.md` § "Threads carried over from an earlier cycle").

## Commit on the PR head with no reply

A commit can be on the PR head while its thread has no reply. `git push` sends every commit ahead of the PR head. So the commit of a thread that got the answer "handle separately" goes along with the push of the other fixes of the cycle. A human can also push a commit of the skill by hand. After such a push, no local commit names the thread, and the thread has no reply. Without this test, a later run takes the thread for a new one, and acts on it again against the answer of the user.

1. Once per cycle, after the fetch of `thread-state-schema.md` § "Ancestry check" command 1, also fetch the base branch: `git fetch origin "+refs/heads/<baseRefName>:refs/remotes/origin/<baseRefName>"`. `baseRefName` is in the PR metadata of Phase 1. If the fetch fails, go to step 6.
2. Run `git log --format='%H %s' origin/<baseRefName>..origin/pull/<prId>/head`. It lists the commits of the PR.
3. A commit names a thread by the rule of § "Local commit with no reply" step 2.
4. Run this test for each thread that is still `fresh-unhandled` after § "Local commit with no reply". If a commit of the PR names the thread, derive `pr-commit-no-reply` instead. Set `claimSource` to `pr-commit` and `claimedSha` to the newest such commit. Set `shaResolvesLocally` and `isAncestorOfRemote` to `true`, and leave `isAncestorOfHead` as `null`. Do not send the thread to Phase 3. A comment in `processedCommentIds` of this session gets no such test.
5. Report: `T#<id> has commit <sha> on the PR head that names it, but no reply about it — the human handles it.`
6. If the fetch of step 1 failed, the run cannot read the commits of the PR. Then a commit of the PR can name any thread with no reply. So derive `pr-commit-no-reply` for each thread that is still `fresh-unhandled` after § "Local commit with no reply". Set `claimSource` to `pr-commit`, and `claimedSha` to `null`. A comment in `processedCommentIds` of this session does not get this state. Report: `T#<id> has no reply, but the fetch of <baseRefName> failed, so the run cannot read the commits of the PR — the next cycle or run tests it again.` The failed fetch is not a blocker. The run asks no question about it, and these threads open no push. The human does not own these threads. The next cycle or run tests each of them again with steps 1 to 5.

This state is report-only in every mode, and no flag changes it, also not the full mode. The run asks no question about the thread, and makes no edit, commit, reply, or resolve for it. The thread opens no push. The rest of this paragraph is about a thread that a commit of the PR names (step 4). The commit is already on the PR head, so no answer changes what a push sends. The human already owns the thread. The state comes after a "handle separately" answer. It also comes with no such answer. One case is a push by hand of a commit of the skill. The other case is a push whose reply post failed, in a session that then ended. Each later run prints the report line again, until the human resolves the thread. A resolved thread drops out at Phase 2 step 2, unless `include-resolved` keeps it in the roster.

## Report modes

These rules apply to the outcomes below:

- With none of `dry-run`, `no-reply`, and `no-commit`, take the default action of the outcome.
- With `no-reply`, ask the user no question. Print the report line of the outcome, and the human handles the thread.
- With `dry-run`, print the same report line, with no question.
- With `no-commit`, `cured` takes its default action. `unconfirmed-commit-claim` asks no question, because the run cannot push (Rules in `SKILL.md`). Print its report line, and the human handles the thread.
- In every mode, also with none of the flags above, an `unconfirmed-commit-claim` thread whose claim opens no push asks no question. Such a claim is not a carried-over claim (Rules in `SKILL.md`): its SHA does not resolve, no clear SHA exists, or the commit is not on the local branch (`isAncestorOfHead: false`). Print its report line, and add `No push can carry this commit. The human handles it.` No answer opens a push for such a claim, so the run asks no question.
- In each later cycle of a `/loop` session (`thread-state-schema.md` § "Session lifecycle"), an `unconfirmed-commit-claim` thread asks no question. The user can be away, and this question holds the whole cycle, not only the push. Print its report line, and add `The human handles it.` The cycle goes on.

## `cured`

The SHA resolves locally and is an ancestor of `origin/pull/<prId>/head`. The fix already landed on the remote through the push of an earlier cycle or invocation, but the resolve call is missing or failed. This is the catch-up path. Normally, the `is_resolved` filter of Phase 2 drops a resolved thread before this step. Always derive this state.

- If `openFindingsMarker` is `true` for the thread (see `thread-state-schema.md`), do not resolve it. Report `T#<id> cured (open findings) — left open.`
- Else call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` and `threadId: <threadNodeId>` from the roster. Also pass `owner`, `repo`, and `pullNumber` from Phase 1. The schema of the tool requires them on every call, although `resolve_thread` does not use their values. A resolve of an already resolved thread does nothing, so an old roster entry does no harm.
- On success, report: `T#<id> resolved — <file>:<line>, commit <sha>.`
- On an MCP error, report: `T#<id> cured — <file>:<line>, commit <sha> — resolve failed (<short reason>), resolve manually via GitHub UI.`

Stage 1 only derives `cured`. Stage 2 makes the resolve call after its own ancestry check (see "Dispatch model" in `SKILL.md`). If that check disagrees, Stage 2 does not act on the thread in this cycle. It prints the `unconfirmed-commit-claim` report line below. Phase 2 step 5 of the next cycle derives the state again, and asks the question (or prints a report line, § "Report modes").

## `unconfirmed-commit-claim`

This outcome covers these cases:

- The SHA resolves locally, but it is not yet an ancestor of the remote. The commit is on the local branch, or it is not (`isAncestorOfHead`).
- The SHA does not resolve to a known commit in this checkout.
- The reply claims a commit, but no SHA comes out of it clearly.
- No reply claims the commit, but an unpushed local commit names the thread (§ "Local commit with no reply"). It uses the report line of that section.

In each case, nothing shows yet that the commit claim is safe to report as ready.

- Do not treat the thread as fresh or unhandled, and do not implement anything new on it.
- No flag skips this outcome, also not the full mode. An unconfirmed SHA needs the input of a human.
- Report: `T#<id> already has an AI reply about a committed fix (commit <sha-or-"unspecified">) that can't be confirmed safe to report as ready — <hasn't landed on the remote yet | the commit isn't on the local branch | this checkout can't resolve the SHA locally | no SHA could be extracted from the reply>.`
- Leave the thread as it is until the user answers. The orchestrating session asks the question, unless § "Report modes" turns it into a report line (see "Dispatch model" in `SKILL.md`). Phase 4 uses the answer (see `commit-push-resolve.md`).
