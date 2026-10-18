# `deep-fix`: one thread through `/research-implement-review-report`

Read this file for a run in which the `deep-fix` parameter names a thread. The parameter row and the rules for `deep-fix` are in `SKILL.md` (Parameters and Rules).

Contents: the override and the ineligible cases, and the place of Stage 3 in the cycle. Then the hand-back of Stage 2, the brief and the outcomes of Stage 3, and the cycle log.

## `deep-fix` override

`deep-fix=<threadId>` (or `T#<threadId>`) can name THIS thread. If the thread is eligible (see below), it does NOT get its normal action from the tag matrix of Phase 3. It goes to **Stage 3** instead. For an automated-review finding, this happens after Phase 3b (see Phase 3b step 5, the second exit). `deep-fix` names exactly one thread per invocation. A human named the thread, and that is the sign of eligibility. No size or tag list applies, only the hard list below.

**Hard ineligibility**. For these cases, decline the `deep-fix` routing with a one-line reason. The thread then gets its normal Phase 3 or Phase 3b classification.

| Declined | Reason |
| --- | --- |
| Automated-review `needs-clarification`, `false-positive`, or `not-applicable` | No fix exists. Phase 3b step 5 and the hard rules of `automated-review-verification.md` never implement these verdicts. |
| `**[ToDiscuss]**` | Never implement a code change only because of a `[ToDiscuss]` thread, with or without `autonomous` (Bucket A2 in `SKILL.md`). |
| `**[OutOfScope]**` | Never implement in this PR (the tag matrix, and Bucket B). |
| `**[Question]**`, `**[Note]**`, or untagged | These tags allow no code change at all. |
| `unconfirmed-commit-claim` | No flag skips this outcome, and the skill implements nothing new on it (Phase 2 step 5). |
| `cured` or `already-assessed`, with no newer human reply | The thread is already final. `deep-fix` does not reopen a settled thread. |
| A fix that reaches outside the diff of the current PR | PR-scope discipline. No flag skips it (Bucket B). |
| `dry-run`, `no-edit`, `strict`, or `no-commit` set for this invocation | These flags forbid edits or commits. `/research-implement-review-report` needs both to run its arc (see the flag precedence in Rules). |

## Place in the cycle

An eligible `deep-fix` thread does NOT run Phase 4 steps 1 to 4. Stage 3 handles it separately, LAST in the cycle. Stage 3 runs after steps 1 to 4 of every other thread, and after the `squash` commit for a run with `squash`. It runs BEFORE the one push of the cycle. With this order, no other commit lands on the branch between the `HEAD` that Stage 3 records and the one commit that it makes.

**Hand-back of Stage 2**. Stage 3 runs in the orchestrating session, not in a dispatch. So on such a cycle, **the dispatch of Stage 2 ENDS** after steps 1 to 4 of every other thread. For a run with `squash`, it ends after the `squash` commit. It always ends BEFORE the push. Stage 2 returns these items to the orchestrating session:

- the `threadId` of the `deep-fix` thread (at minimum)
- its `filePath` and line range, and the text of the reviewer word for word
- its tags, or its automated-review verdict and confidence
- the SHAs that Stage 2 committed in this cycle, or the one `squash` SHA
- the threads that Stage 2 already replied to

The orchestrating session then runs Stage 3 and dispatches Stage 3b. It owns the push, the resolve, and Phase 5 of this cycle, and Stage 2 does none of these. On a cycle without an eligible `deep-fix` thread, nothing changes. Stage 2 then runs Phase 4 through the resolve, and Phase 5.

## Stage 3 — `deep-fix` brief and outcomes

**Pre-flight: find the checkout root before any dispatch**. Get the local checkout root with `git rev-parse --show-toplevel`. Use that ABSOLUTE path as the worktree path in the brief below. Then find out whether `git rev-parse --abbrev-ref HEAD` in that root equals the `headRefName` of the PR. Phase 2 step 5 does not assume this. If a command fails or the branch differs, STOP. Ask the user before you check out or switch a branch, or create anything.

**Invocation**. Stage 3 runs `/research-implement-review-report` as the next phase of the orchestrating session. It never goes into the Stage 2 brief, because a phase that runs its own subagents is its own dispatch (`dev-essentials:subagent-orchestration` Rule 1). It never goes to a subagent. That command can stop on a question, and with `interactive` on its Phase 1 sign-off gate. Questions and that gate belong to the session that talks to the user. Pass:

1. The **branch name** (the `headRefName` of the PR) and the **absolute worktree path**. That command needs these two facts for its pre-existing-branch verification step.
2. `--base=<baseRefName>`: the target branch of the PR, which Phase 1 cached.
3. `--commit-mode=single` and `--rounds=<deep-fix-rounds>`.
4. **Commit subject**. The one squash commit MUST use the format of Phase 4 step 3 of this skill. The subject is `PR #<prId> T#<threadId>: <subject>`. The body explains *why* and names the point of the reviewer. The commit ends with the `Co-Authored-By` trailer.
5. **Squash window**. No other commit lands on this branch between the recorded `HEAD` and the squash (see "Place in the cycle"). The safety stop of that command for the squash base can still trip. Then let it stop and report. Do not override it.
6. **Scope**. The fix stays inside the files and areas that the PR diff already touches, and it addresses only this thread.
7. **Artifacts**. Never stage or commit the research, plan, or report artifacts of that command. Never put their paths in the thread reply or the commit message. Pipeline-internal artifacts stay out of anything that ships (`dev-essentials:engineering-discipline` Rule 3).
8. **No push**. This skill owns the one push of the cycle. `/research-implement-review-report` never pushes without an explicit go-ahead of the user.
9. Expect back: the squash SHA, the stop verdict of the review loop, the round count, and the list of deferred findings. The stop verdict is `stop-clean`, `stop-max-rounds`, or `stop-blocked`.
10. `--interactive` or `--autonomous`, for an invocation with `interactive` or `autonomous`.

**Reply and resolve, by stop verdict**. Stage 3b is a one-shot GitHub dispatch (Rule 4) on the model that the dispatch table of `SKILL.md` gives it. It posts the reply and the resolve after Stage 3 reports its squash SHA, its stop verdict, and its round count:

| Verdict | Commit? | Tree | Reply | Resolved after push? |
| --- | --- | --- | --- | --- |
| `stop-clean` | Yes (one squash SHA) | Green | The "Implemented fix" template, plus one clause that names the arc | Yes, by the normal rule (`commit-push-resolve.md`) |
| `stop-max-rounds` | Yes | Green | The "Implemented fix" template, plus an explicit line on the open work | No. It stays open with `openFindingsMarker: true`. |
| `stop-blocked` | No (nothing kept) | Red | Nothing by default. STOP and ask the user. | No |

`stop-clean` reply:

```text
**[AI]** **[[T#<threadId>](<html_url>)]**

Fixed: <one-line summary>. Implemented via a research → plan → review cycle (<N> review rounds, clean). Committed as <short-sha>; will be included in the next push.
```

`stop-max-rounds` reply:

```text
**[AI]** **[[T#<threadId>](<html_url>)]**

Fixed: <one-line summary>. Implemented via a research → plan → review cycle (<N> review rounds). Committed as <short-sha>; will be included in the next push.

Open findings remain; leaving this thread open: <1-2 line list>.
```

Both replies are affirmative commit claims under the existing `Committed as <sha>` match. So Phase 2 step 5 and the resolve step of Phase 4 work without a new state machine. The last sentence of the `stop-max-rounds` reply STARTS WITH the `openFindingsMarker` phrase that a later cycle matches. The match is a prefix match on `Open findings remain; leaving this thread open`, with any punctuation (see `thread-state-schema.md`).

Never link the report artifact of that command from either reply. It is a pipeline-internal artifact (`dev-essentials:engineering-discipline` Rule 3). The reply summarizes the arc, the round count, and the verdict instead.

**`stop-blocked`: cancel the push of the cycle**. With `--commit-mode=single`, `/research-implement-review-report` makes the commits of each review-loop round on the PR source branch. It makes them before it can know that the build is red. The rule of Phase 4 step 1 (no commit after a failed build) cannot stop commits that the arc of that command already made. So:

- Do NOT squash. Do NOT post a `**[AI]**` "Fixed" reply. Do NOT post `**[AI][Draft]**` either. `automated-review-verification.md` keeps that prefix for a proposal, and a half-finished commit stack is not a proposal.
- **Cancel the push of this cycle completely**, for the commits of every thread, not only for this one. STOP, and tell the user two facts: red commits already sit on the PR source branch, and a push publishes a broken PR.
- In Phase 5, report it as `deep-fix — blocked (build red, not pushed)`.
- Offer the two real ways to recover: fix forward in this session, or reset the branch to the SHA from before Stage 3. Use a new commit or `git reset` on this **unpushed** tip only. Bucket B still forbids an amend or a rewrite of *pushed* history.

## Cycle log on a `deep-fix` cycle

The row of a `deep-fix` thread shows one of these outcomes: `deep-fix (N rounds, clean)`, `deep-fix — open findings`, or `deep-fix — blocked`. See `thread-state-schema.md` § "Cycle log" for the full list. A cycle whose `deep-fix` run ended `stop-blocked` prints `deep-fix — blocked (build red, not pushed)` in place of the usual line about the push state. The push of that cycle is cancelled.

**On a `deep-fix` cycle, the ORCHESTRATING SESSION prints the whole cycle log, not Stage 2**. The dispatch of Stage 2 already ended after Phase 4 step 4. The orchestrating session builds the rows from the results that Stage 2 returned. It adds the squash SHA, the stop verdict, and the round count of Stage 3.
