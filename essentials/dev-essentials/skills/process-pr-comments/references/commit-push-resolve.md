# Commit, reply, push, and resolve (Phase 4)

Stage 2 runs steps 1 to 4 and the resolve step. Stage 2 never runs the push. The orchestrating session runs it, after steps 1 to 4 of every thread, and then resumes Stage 2 for the resolve step. On a `deep-fix` cycle, Stage 2 runs steps 1 to 4 only. The orchestrating session then owns the push, the resolve, and Phase 5 (see `deep-fix.md`).

## Contents

- Steps for each thread
- Push, once per cycle
- Resolve threads and report
- Threads carried over from an earlier cycle
- One file, several threads
- Threads with the same note
- Reply templates
- Thread resolution after a fix lands: the `no-reply` split
- Which threads to resolve

Contents: the steps for each thread, the push, the resolve, carried-over threads, the reply templates, the `no-reply` split, and the threads to resolve.

The reply comes right after the commit and before the push. So the reply never claims too much: it reports a local commit, not a change that a reviewer can already see. A resolve says more: it tells the reviewer that the fix is visible. That is true only after the push lands. So the skill resolves a thread only after the push of its fix landed, never before. The push needs an explicit go-ahead of the user for each push (see Rules in `SKILL.md`), unless `autonomous` is set. It comes once per cycle, after every thread below is built, tested, committed, and replied to.

To resolve a thread, call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` and `threadId`. The schema of the tool also requires `owner`, `repo`, and `pullNumber` on every call, although `resolve_thread` does not use their values. Pass the values from Phase 1. A resolve of an already resolved thread does nothing.

## Steps for each thread

Do these steps in order for each thread that this cycle fixes, before you go on to the next thread.

**Exception for `squash`**. Steps 1 and 2 still run for each thread in this loop. The one commit of step 3 does not exist until the end of the cycle. So the reply of step 4 cannot name a SHA for each thread yet. Run steps 1 and 2 for every thread first, and make the one commit at the end of the cycle. THEN run step 4 for every thread, each reply with that one shared SHA. Then go on to the push.

**Exception for `deep-fix`**. An eligible thread that `deep-fix` names does not run steps 1 to 4 here. It goes to Stage 3 (see `deep-fix.md`).

1. **Build and test**: build the affected projects and run the affected tests. If the build fails or a test regresses, do not commit.
2. **Stage**: `git add` only the files that this thread touched. Never `git add -A` or `git add .`.
3. **Commit**: make one commit for each thread (default). A local `git commit` gives a real SHA at once, before any push. Message format:

   ```text
   PR #<prId> T#<commentId>: <short imperative summary>

   <1-3 lines explaining *why*, referencing the reviewer's point>

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   - With `squash`, do not run step 4 after each thread (see the exception above). First collect the fixes of steps 1 and 2 for every thread. Then make ONE commit at the end of the cycle, with every `T#<id>` in the body. Only then run step 4 for each thread.
   - With `no-commit`, skip the commit and the push. Leave the edits staged for the human, and reply with the "staged" template below.
   - **Do not ask the user to approve a commit**. Commits stay automatic. The push is different (see below). Feedback of the user on an earlier cycle, for example "LGTM, proceed", does not change the commit default to `no-commit`. A user who wants to inspect before the commit says so with the `no-commit` flag.
4. **Reply** with `mcp__plugin_github_github__add_reply_to_pull_request_comment` and the templates below. Name the LOCAL commit SHA of step 3. The reply does not claim a push. The reply is the lasting record of the commit, and the skill writes no other state. In a later cycle, Phase 2 step 5 finds the committed-but-unpushed state again from this reply text. It runs `git merge-base --is-ancestor` against the remote. This works in the same invocation and in a later one.

Repeat steps 1 to 4 for every thread of the cycle before the push.

## Push, once per cycle

The orchestrating session pushes after steps 1 to 4 ran for every thread of the cycle. The push needs an explicit go-ahead of the user in the current turn (see Rules in `SKILL.md`). The approval of an earlier cycle does not carry over. With `autonomous`, push as soon as every thread of the cycle is committed and replied to (with `no-reply`: committed).

- Run `git push` once for all commits of the cycle. This holds for one commit for each thread and for one `squash` commit: exactly one push per cycle.
- Never force-push. Never push to a protected branch, or to any branch other than the PR source branch.
- If the go-ahead did not come before the cycle log, leave the commits unpushed. Say so in Phase 5: `N commits ready, not yet pushed — push when ready`. The posted replies stay correct, because they claim a commit, never a push. No thread of this cycle is resolved until the push lands.
- **Exception**: a `deep-fix` run of this cycle that ended `stop-blocked` cancels the whole push of the cycle, not only for that thread (see `deep-fix.md`).

## Resolve threads and report

This step runs after the push of this cycle succeeds. It covers two groups of threads: (a) the threads that this cycle committed and replied to, and (b) each thread that Phase 2 step 5 marked `unconfirmed-commit-claim` in this cycle.

**Group (a), the threads of this cycle**. Skip a thread with `openFindingsMarker: true` (see `deep-fix.md`). For each other thread, run the ancestry check (`thread-state-schema.md` § "Ancestry check") for its commit SHA against `<pushed-tip>`. `<pushed-tip>` is the commit or branch state that the push of this cycle produced, not the remote-tracking ref.

- The check passes. This is the normal case, because the push carried the commit. Call `pull_request_review_write` with `method: resolve_thread`, `threadId: <threadNodeId>` from the Phase 2 roster, and `owner`, `repo`, and `pullNumber` from Phase 1.
  - On success, report: `T#<id> resolved — <file>:<line>, commit <sha> pushed as part of this cycle.`
  - On an MCP error, report: `T#<id> pushed but resolve failed (<short reason>) — resolve manually via GitHub UI.`
- The check fails: the commit is not on the pushed branch, for example because it was dropped or rebased away. Do not call resolve. Report the thread as still open. Do not guess.

**Group (b), the `unconfirmed-commit-claim` threads of this cycle**. The resolve depends on the answer of the human to the question of Phase 2 step 5, not on the ancestry alone. The answer lives in the conversation of this session or `/loop` run, not in a file. It has to last only until Phase 4 of this cycle. Both of these conditions must hold before you resolve such a thread:

1. In this session, the human explicitly answered that question with a push-and-resolve direction for this thread.
2. For a thread with a SHA, the ancestry check against `<pushed-tip>` now passes. For a thread with no SHA, nothing can be tested, and only the direction of the human can lead to a resolve.

Then resolve and report as in group (a), in this cycle. Do not wait for a later cycle. In these cases, leave the thread open:

- The human did not answer, or answered "handle separately" or the like. The push alone does not resolve the thread.
- The check still fails, because the push of this cycle did not carry the commit. Phase 2 step 5 of a later cycle tests it again.

## Threads carried over from an earlier cycle

A fix can be committed and replied to in an earlier cycle or invocation that ended before its push. No state file tracks such a thread. Instead, Phase 2 step 5 finds the state again at the start of each cycle. It reads the existing `**[AI]** Fixed: ... Committed as <sha>` reply of the thread, and runs the ancestry check against `origin/pull/<prId>/head`. If the check passes, because a later push landed the commit, Phase 2 resolves the thread as a catch-up step. If the check fails, Phase 2 asks the user and does not handle the thread again silently. `autonomous` does not skip this question.

In normal runs, this catch-up path is rare. After a resolve call succeeds, `is_resolved` of the thread becomes true on GitHub, and the Phase 2 filter drops the thread in each later fetch. The path exists for a failed resolve call, and for a reply from a time before the skill resolved threads. It works across sessions and invocations, because it depends on the thread history of GitHub and on real git ancestry, not on a file.

If the push approval does not come in this cycle, or the push fails, no thread of this cycle is resolved. The threads stay open with their replies. After the push lands, Phase 2 step 5 of a later cycle finds the reply and resolves the thread. A new try of the same push does the same. The cycle log already shows `N commits ready, not yet pushed — push when ready`.

## One file, several threads

If one file holds the edits of several threads, capture the final state of the file. Then reset the file to `HEAD`. Apply the edit of each thread again, and commit it, before you go on to the next thread.

## Threads with the same note

If three or more threads carry the **same note of the reviewer** at different call sites, treat them as one fix. Make one commit, and reply on each thread with the shared SHA.

## Reply templates

Each reply starts with a **leading tag part** on the FIRST line. It has the `**[AI]**` or `**[AI][Draft]**` marker, and other bold reviewer-style tags as needed. At its end, it has a bold `**[T#<commentId>]**` thread tag as a deep link.

**Link format of the T# tag**. Use the `html_url` field of the comment from `pull_request_read`. Do not build the URL by hand (see `dev-essentials:github-mcp-conventions` § "Thread anchors and `html_url`").

```markdown
**[[T#<commentId>](<html_url>)]**
```

Order of the tags on the first line:

```text
**[AI]** [optional auxiliary tags] **[[T#<commentId>](<html_url>)]**
<blank line>
<body>
```

Templates:

- Implemented fix, committed locally (the push is a later step with its own gate): `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nFixed: <one-line summary>. Committed as <short-sha>; will be included in the next push.`
- Implemented fix with `no-commit`: `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nFixed: <one-line summary>. Diff staged locally, awaiting your commit.`
- Issue created: `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nTracked as issue #<id>: <title>.`
- Draft (automated review, Question, or non-trivial Suggestion): `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**\n\n<analysis>\n\n*Draft pending author confirmation.*`
- Optional suggestion declined or deferred: `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**\n\nOptional — keeping current shape; happy to change if preferred. Reason: <one line>.`
- Override applied (`just fix it`): the first line stays `**[AI]** **[[T#<commentId>](<html_url>)]**`. The body starts with `Per your "just fix it" direction: …`, so that the waiver can be traced.
- Override applied (`draft first`): the first line stays `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**`. The body starts with `Draft per your request: …`.

For a reference to another thread in the body, use the same linked form. Take the `html_url` of the target comment from the Phase 2 roster. Never build URLs by hand.

For the tone and the length of a reply, follow `review-principles.md`.

## Thread resolution after a fix lands: the `no-reply` split

- **Without `no-reply` (default)**: reply, then resolve, with the steps above.
- **With `no-reply`**: do not post the `**[AI]** Fixed` reply, and do not resolve the thread automatically. The reply is the record of why the thread is resolved, so without it the skill does not resolve. Report the cured thread to the user in chat instead, with the file path, the line range, and the commit SHA. Example: `T#<id> cured — <file>:<line>, commit <sha> — resolve manually via the GitHub UI when ready`. The user resolves the thread after a review of the committed diff. This holds for a new fix in Phase 4 and for a catch-up in Phase 2 step 5.

## Which threads to resolve

The skill calls `resolve_thread` (with the node ID of the thread) only for a thread that meets the rule above: committed, replied to, and pushed. It never resolves on a guess, and never resolves a thread that it did not fix.

Resolve these threads after they meet the rule, where the change clearly addresses the point of the reviewer:

- `[ToFix]` and `[Performance]` threads
- automated-review findings where the skill implemented the change

Never resolve these threads:

- false-positive analysis threads (the reviewer reads and resolves them at their own pace)
- `[Note]` threads and threads with only an acknowledgement
- summary banners of an automated review (never touch them at all)
- out-of-scope items (leave them open after the reply about the tracking issue)
- a thread whose `deep-fix` run ended `stop-max-rounds` with open findings (`openFindingsMarker: true`, see `deep-fix.md`)
- every thread that does not meet the rule yet

Never call `unresolve_thread`, unless the user explicitly asks to reopen a specific thread.
