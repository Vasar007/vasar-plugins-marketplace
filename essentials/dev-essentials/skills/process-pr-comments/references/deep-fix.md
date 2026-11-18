# `deep-fix`: one thread through `/research-implement-review-report`

Read this file for a run in which the `deep-fix` parameter names a thread. The parameter row and the rules for `deep-fix` are in `references/parameters.md` and in `SKILL.md` (Rules).

Contents: the override and the ineligible cases, and the place of Stage 3 in the cycle. Then the brief and the outcomes of Stage 3, and the cycle log.

## `deep-fix` override

`deep-fix=<commentId>` (or `T#<commentId>`) can name this thread. If the thread is eligible (see below), it does not get its normal action from the tag matrix of Phase 3. It goes to **Stage 3** instead. For an automated-review finding, this happens after Phase 3b (see Phase 3b step 5, the second exit). `deep-fix` names exactly one thread per invocation. A human named the thread, and that is the sign of eligibility. No size or tag list applies, only the hard list below.

**Hard ineligibility**. For these cases, decline the `deep-fix` routing with a one-line reason. The thread then gets its normal Phase 3 or Phase 3b classification.

| Declined | Reason |
| --- | --- |
| Automated-review `needs-clarification`, `false-positive`, or `not-applicable` | No fix exists. Phase 3b step 5 and the hard rules of `automated-review-verification.md` never implement these verdicts. |
| `**[ToDiscuss]**` | Never implement a code change only because of a `[ToDiscuss]` thread, in every mode (Bucket A2 in `SKILL.md`). |
| `**[OutOfScope]**` | Never implement in this PR (the tag matrix, and Bucket B). |
| `**[Question]**`, `**[Note]**`, or untagged | These tags allow no code change at all. |
| `unconfirmed-commit-claim` | No flag skips this outcome, and the skill implements nothing new on it (Phase 2 step 5). |
| `pr-commit-no-reply` | A commit of the PR already names the thread, and the human owns it. Or the fetch of the base branch failed, and the run cannot read the commits of the PR. No flag changes this (`committed-fix-state.md` § "Commit on the PR head with no reply"). The decline prints the report line of that section. It does not send the thread to Phase 3. |
| `cured` or `already-assessed`, with no newer human reply | The thread is already final. `deep-fix` does not reopen a settled thread. |
| A fix that reaches outside the diff of the current PR | PR-scope discipline. No flag skips it (Bucket B). |
| `dry-run`, `no-edit`, `strict`, or `no-commit` set for this invocation | These flags forbid edits or commits. `/research-implement-review-report` needs both to run its arc (see the flag precedence in Rules). |

## Place in the cycle

An eligible `deep-fix` thread does not run Phase 4 steps 1 to 4. Stage 3 handles it separately, after the other threads. Stage 3 runs after steps 1 to 4 of every other thread, and after the `squash` commit for a run with `squash`. It runs before the one push of the cycle. With this order, no other commit lands on the branch between the `HEAD` that Stage 3 records and the one commit that it makes.

**Stage 2 around Stage 3**. Stage 2 and Stage 3 both run in the orchestrating session. On such a cycle, Stage 2 first runs steps 1 to 4 of every other thread. For a run with `squash`, it also makes the `squash` commit. Then Stage 3 runs. The post of the replies, the push, the resolve, and Phase 5 of this cycle come after Stage 3. The session asks the open items of Stage 2 with its question for the go-ahead (in the full mode, before the post). It uses the answers in the post: the approved `[Question]` replies and the approved issue fields. If an answer asks for a code change, the rule for a changed fix applies (`commit-push-resolve.md` § "When replies post").

## Stage 3 — `deep-fix` brief and outcomes

**Pre-flight: find the checkout root before any dispatch**. Get the local checkout root with `git rev-parse --show-toplevel`. Use that absolute path as the worktree path in the brief below. Then find out whether `git rev-parse --abbrev-ref HEAD` in that root equals the `headRefName` of the PR. Phase 2 step 5 does not assume this. If a command fails or the branch differs, stop. Ask the user before you check out or switch a branch, or create anything.

**Invocation**. Stage 3 runs `/research-implement-review-report` as the next phase of the orchestrating session. It never goes into the brief of a subagent, because a phase that runs its own subagents is its own dispatch (`dev-essentials:subagent-orchestration` Rule 1). That skill can stop on a question, and in the interactive mode on its Phase 1 sign-off gate. Questions and that gate belong to the session that talks to the user. Pass:

1. The **branch name** (the `headRefName` of the PR) and the **absolute worktree path**. That skill needs these two facts for its pre-existing-branch verification step.
2. `--base=<baseRefName>`: the target branch of the PR, which Phase 1 cached.
3. `--commit-mode=single` and `--rounds=<deep-fix-rounds>`.
4. **Commit subject**. The one squash commit must use the format of Phase 4 step 3 of this skill. The subject is `PR #<prId> T#<commentId>: <subject>`. The body explains *why* and names the point of the reviewer. The commit ends with the `Co-Authored-By` trailer.
5. **Squash window**. No other commit lands on this branch between the recorded `HEAD` and the squash (see "Place in the cycle"). The safety stop of that skill for the squash base can still trip. Then let it stop and report. Do not override it.
6. **Scope**. The fix stays inside the files and areas that the PR diff already touches, and it addresses only this thread.
7. **Artifacts**. Never stage or commit the research, plan, or report artifacts of that skill. Never put their paths in the thread reply or the commit message. Pipeline-internal artifacts stay out of anything that ships (`dev-essentials:engineering-discipline` Rule 3).
8. **No finish steps**. This skill owns the one push of the cycle. Tell `/research-implement-review-report` not to run its Phase 5 (Finish). When another workflow runs that skill, it skips the phase anyway.
9. Expect back: the squash SHA, the stop verdict of the review loop, the round count, and the list of deferred findings. The stop verdict is `stop-clean`, `stop-max-rounds`, or `stop-blocked`. On `stop-blocked`, do not squash. Keep the round commits as they are.
10. The `--mode` of the invocation.
11. **Review scope**. Run the review loop of that skill with `target=diff <recorded-HEAD>..HEAD`, the range of this arc only, not `target=branch`.

**Reply and resolve, by stop verdict**. The orchestrating session posts the batch itself, right before the push of the cycle: after the go-ahead, or in the full mode as the Rules in `SKILL.md` say. Stage 3 reported its squash SHA, its stop verdict, and its round count before that. First, the session has Task Composer create each `[OutOfScope]` issue whose fields Stage 2 or the answers approved. Then it posts the batch: the reply of the `deep-fix` thread, every pending reply of Stage 2, and the replies of the approved open items. A failed post follows the second exception of `SKILL.md` § "What Stage 2 can still call". The table gives the reply of the `deep-fix` thread:

| Verdict | Commit? | Tree | Reply | Resolved after push? |
| --- | --- | --- | --- | --- |
| `stop-clean` | Yes (one squash SHA) | Green | The "Implemented fix" template, plus one clause that names the arc | Yes, by the normal rule (`commit-push-resolve.md`) |
| `stop-max-rounds` | Yes | Green | The "Implemented fix" template, plus an explicit line on the open work | No. It stays open with `openFindingsMarker: true`. |
| `stop-blocked` | Yes, red (the commits of the arc stay on the unpushed tip) | Red | Nothing by default. Stop and ask the user. | No |

After the push of the cycle lands, the orchestrating session itself runs the resolve step of `commit-push-resolve.md` § "Resolve threads and report". It does this for every fixed thread of the cycle, the `deep-fix` thread included.

`stop-clean` reply:

```text
**[AI]** **[[T#<commentId>](<html_url>)]**

Fixed: <one-line summary>. Implemented via a research → plan → review cycle (<N> review rounds, clean). Committed as <short-sha>; will be included in the next push.
```

`stop-max-rounds` reply:

```text
**[AI]** **[[T#<commentId>](<html_url>)]**

Fixed: <one-line summary>. Implemented via a research → plan → review cycle (<N> review rounds). Committed as <short-sha>; will be included in the next push.

Open findings remain; leaving this thread open: <1-2 line list>.
```

Both replies are affirmative commit claims under the existing `Committed as <sha>` match. So Phase 2 step 5 and the resolve step of Phase 4 work without a new state machine. The last sentence of the `stop-max-rounds` reply STARTS WITH the `openFindingsMarker` phrase that a later cycle matches. The match is a prefix match on `Open findings remain; leaving this thread open`, with any punctuation (see `thread-state-schema.md`).

Never link the report artifact of that skill from either reply. It is a pipeline-internal artifact (`dev-essentials:engineering-discipline` Rule 3). The reply summarizes the arc, the round count, and the verdict instead.

**`stop-blocked`: cancel the push of the cycle**. With `--commit-mode=single`, `/research-implement-review-report` makes the commits of each review-loop round on the PR source branch. It makes them before it can know that the build is red. The rule of Phase 4 step 1 (no commit after a failed build) cannot stop commits that the arc of that skill already made. So:

- Do not post a `**[AI]**` "Fixed" reply. Do not post `**[AI][Draft]**` either. `automated-review-verification.md` keeps that prefix for a proposal, and a half-finished commit stack is not a proposal.
- **Cancel the push of this cycle completely**, for the commits of every thread, not only for this one. Stop, and tell the user two facts: red commits already sit on the PR source branch, and a push publishes a broken PR.
- The pending replies of the other threads stay unposted, because the push of the cycle does not come. A later "push" of the user does not post them or push this cycle (Bucket B). The way back is a new invocation of the skill after the recovery below (`commit-push-resolve.md` § "When replies post").
- In Phase 5, report it as `deep-fix — blocked (build red, not pushed)`.
- Offer the two real ways to recover: fix forward in this session, or reset the branch to the SHA from before Stage 3. Use a new commit or `git reset` on this **unpushed** tip only. Bucket B still forbids an amend or a rewrite of *pushed* history.

## Cycle log on a `deep-fix` cycle

The row of a `deep-fix` thread shows one of these outcomes: `deep-fix (N rounds, clean)`, `deep-fix — open findings`, or `deep-fix — blocked`. See `thread-state-schema.md` § "Cycle log" for the full list. A cycle whose `deep-fix` run ended `stop-blocked` prints `deep-fix — blocked (build red, not pushed)` in place of the usual line about the push state. The push of that cycle is cancelled.

On a `deep-fix` cycle, the cycle log also gives the squash SHA, the stop verdict, and the round count of Stage 3.
