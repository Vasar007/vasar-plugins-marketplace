---
name: process-pr-comments
description: Process GitHub pull-request review comments as the PR author, using the review-tag taxonomy ([ToFix], [Optional], [Suggestion], [Question], [ToDiscuss], [Performance], [OutOfScope], [Note], [PX], [Repetition]) and the special automated-review header. Skips threads GitHub already marks resolved or outdated (`isResolved`/`isOutdated`) before classifying anything. Classifies every remaining comment, implements small fixes (including obvious, narrowly-scoped automated-review findings) directly, drafts larger or ambiguous ones, re-verifies automated review proposals before replying, delegates issue creation to Task Composer, and posts [AI]-prefixed replies; once a fix's commit is confirmed pushed, the skill resolves that thread itself via GitHub MCP's `pull_request_review_write` (`method: resolve_thread`). Commit is eager and automatic; push is a separate, explicitly user-gated step (unless `auto-push`/`autonomous` is set) that happens once per cycle, after every thread's reply is posted. Runs once by default; opt in to a polling monitor with the `loop` flag (default cadence 15m), or route one named thread through `/research-implement-review-report`'s research → plan → review cycle with the opt-in `deep-fix=<threadId>` flag. Triggers on requests like "process PR comments", "work through review feedback", "handle GitHub PR comments", "respond to reviewers", "address review comments", "monitor PR for new comments", or a GitHub PR URL with a request to act on its feedback.
---

# Process PR Review Comments

## Purpose

Acts on review comments **as the PR author**. Before classifying anything, Phase 2 filters out threads GitHub itself already marks `isResolved` or `isOutdated` (real fields returned by `pull_request_read` `get_review_comments` — confirmed in this MCP server's tool schema), so the skill never spends a reply on a dead conversation. Classifies each remaining comment by its review tag, applies a tiered response workflow (implement small fixes, draft larger ones, answer questions, delegate tracking issues), and posts a concise `**[AI]**`-prefixed reply (Markdown bold, matching the reviewer convention of bolding leading tags like `**[ToFix]**`) so reviewers can distinguish Claude's responses from the author's. Once a fix is committed locally, the `**[AI]** Fixed` reply is posted immediately, referencing the local commit SHA — before push. Once that commit's push actually lands (whichever cycle or invocation that happens in — see Phase 2 step 5 and Phase 4), the skill resolves the thread itself by calling `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` — this MCP server's tool surface does expose thread resolution, contrary to an earlier iteration of this skill's assumption. Pushing is a separate, explicitly user-gated step (unless `auto-push` is set for that invocation) — see Phase 4 — that happens once per cycle, after every thread's fix has been committed and replied to.

## When to use

- User asks to process, work through, or address PR review comments.
- User pastes a GitHub PR URL or a PR number and asks for comment handling.
- User wants a recurring monitor ("every 15 minutes check for new comments").
- Automated review bots (e.g., GitHub Actions, Copilot, CodeRabbit) have commented on the PR and the user wants verified, drafted responses.

## When NOT to use

- Reviewing code written by someone else — that is the reviewer side, handled by other workflows.
- Creating a PR, editing its description, changing reviewers.
- Resolving or unresolving a thread this skill did not itself fix — the skill only ever resolves a thread it committed, replied to, AND actually pushed a fix for in this session (see Phase 4); it never resolves a thread on the reviewer's behalf for any other reason, and never calls `unresolve_thread` unless the user explicitly asks to reopen one.

## Prerequisites

1. GitHub MCP tools (`mcp__plugin_github_github__*`) must be available. If missing, stop and ask the user to reconnect via `/mcp` before retrying (see `dev-essentials:github-mcp-conventions` Rule 5).
2. The user must supply the explicit **`owner`** and **`repo`** pair (or a full GitHub PR URL from which they can be parsed). Never infer from git remote or session context (see `dev-essentials:github-mcp-conventions` Rule 1).
3. The Task Composer agent (`task-composer` from `dev-essentials`) must be loaded when an issue needs to be created for `[OutOfScope]` comments.
4. `deep-fix` additionally requires `/research-implement-review-report` to be available as a command in this plugin. If it is not, decline the `deep-fix` routing with a one-line reason and fall through to normal Phase 3/3b classification (see Rules and Phase 3's `deep-fix` override).

## Parameters

Accept free-form `key=value` pairs and standalone flags from skill args. All are optional except where noted.

| Param               | Values                                           | Default                     | Meaning                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|----------------------|---------------------------------------------------|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `pr`                | `<id>` or full GitHub PR URL                     | Required                    | Target PR. A full URL supplies `owner`, `repo`, and `pullRequestNumber`; those override other params.                                                                                                                                                                                                                                                                                                                                                    |
| `owner`             | GitHub org or username                           | Parsed from URL or required | Repository owner. Must be supplied verbatim — never inferred.                                                                                                                                                                                                                                                                                                                                                                                             |
| `repo`              | Repository name                                  | Parsed from URL or required | Repository name. Must be supplied verbatim — never inferred.                                                                                                                                                                                                                                                                                                                                                                                              |
| `interval`          | `5m`, `15m`, `30m`, `1h`, `<N>m`                 | `15m`                       | Polling cadence when `loop` is set. Ignored otherwise.                                                                                                                                                                                                                                                                                                                                                                                                    |
| `loop`              | flag                                              | off                         | Opt IN to monitoring — after the first cycle, auto-enter `/loop` at `interval` (see Phase 6). Without this flag the skill runs a single pass and stops. Incompatible with `deep-fix` — see Rules.                                                                                                                                                                                                                                                       |
| `dry-run`           | flag                                              | off                         | Analyze and report in chat only. No replies, no edits.                                                                                                                                                                                                                                                                                                                                                                                                    |
| `tags`              | comma-separated tag names, e.g. `ToFix,Question` | all                         | Process only these tags this cycle. Tag names match without brackets.                                                                                                                                                                                                                                                                                                                                                                                     |
| `no-reply`          | flag                                              | off                         | Do not post thread replies; code edits still allowed.                                                                                                                                                                                                                                                                                                                                                                                                     |
| `no-edit`           | flag                                              | off                         | Draft-only; never edit files, even for trivial fixes.                                                                                                                                                                                                                                                                                                                                                                                                     |
| `no-commit`         | flag                                              | off                         | Edit and stage locally only — do NOT commit or push. Useful for review sessions where the human wants to inspect.                                                                                                                                                                                                                                                                                                                                        |
| `squash`            | flag                                              | off                         | Bundle all fixes from this cycle into one commit instead of one commit per thread. Push (once per cycle) is still gated by explicit approval unless `auto-push`/`autonomous` is set.                                                                                                                                                                                                                                                                    |
| `auto-push`         | flag                                              | off                         | Skip the per-push approval gate for this invocation — commit, reply, and push proceed automatically within the same cycle. Resolution still follows automatically once that push lands (Phase 4) — same as the default gated path, just without waiting on the push approval itself. See the flag-precedence order in Rules (`dry-run`/`no-commit`/`no-reply` still win over `auto-push`). Combined with `no-reply`, replies stay suppressed as usual — `auto-push` only removes the push-approval gate.       |
| `autonomous`        | flag                                              | off                         | Full autonomy — bypasses every human-decision gate listed in the "Autonomy" section's Bucket A (implement Medium/Large `[ToFix]` and non-trivial `[Suggestion]`/`[Optional]` directly; post `[Question]`/`[ToDiscuss]` replies and automated-review obviousness-test failures without waiting) and implies `auto-push`'s behavior. Never bypasses the structural safety rules in Bucket B, or an active "pause for my review" block. See the flag-precedence order in Rules. Off by default. |
| `strict`            | flag                                              | off                         | Pause before every file edit regardless of size.                                                                                                                                                                                                                                                                                                                                                                                                          |
| `include-resolved`  | flag                                              | off                         | Also process threads Phase 2 would otherwise filter out because `isResolved` or `isOutdated` is true. Rarely useful.                                                                                                                                                                                                                                                                                                                                                                                                      |
| `deep-fix`          | `<threadId>` or `T#<threadId>`                   | off                         | Opt-in, per-thread escape hatch: route this ONE thread's fix through `/research-implement-review-report` (research → plan → sign-off → implement → review loop → report) with `--commit-mode=single`, instead of this skill's own inline fix path. No size/tag whitelist — a human naming the thread is the signal — but a hard ineligibility list still applies (see Phase 3's `deep-fix` override). Exactly one thread per invocation. When the named thread is ineligible, or `dry-run`/`no-edit`/`strict`/`no-commit` is also set, the `deep-fix` ROUTING is declined with a one-line reason and that thread falls through to its normal Phase 3/3b classification instead — neither the invocation nor the thread is aborted. Incompatible with `loop` (see Rules). See Phase 3's `deep-fix` override and Phase 4's "Deep-fix dispatch". |
| `deep-fix-rounds`   | `<N>`                                             | `2`                         | Review-loop cycle count forwarded verbatim to `/research-implement-review-report`'s `--rounds`. Ignored unless `deep-fix` is also set.                                                                                                                                                                                                                                                                                                                   |

### Rules

- **One PR per invocation.** Re-invoke the skill to target a different PR.
- **Linked PRs are read-only context.** When a comment references another PR, the skill MAY read that PR's description, threads, or diff for context. It MUST NOT classify or act on comments belonging to any PR other than the target.
- **Commit eagerly after every implemented fix** — default is one commit per thread, created locally immediately, without waiting for approval first. Follow-up commits after user feedback are normal (don't amend, don't rebase). Opt out with `no-commit` (explicit user request to inspect before committing); bundle under one commit with `squash`. See Phase 4.
- **Flag precedence (highest wins), stated once here — every other mention in this skill is a pointer back to this line:** an active "pause for my review" instruction (or equivalent) > `dry-run`/`no-commit` > `no-reply` > `strict`/`no-edit` > `autonomous`/`auto-push` > default gated behavior. `dry-run`/`no-commit` win next (nothing is committed or pushed). `no-reply` wins next (no thread replies, even if edits/commits proceed). `strict`/`no-edit` win next (no edits without per-edit approval). Only once none of those apply do `autonomous`/`auto-push` take effect (skip the per-push approval gate). With nothing set, the default gated behavior applies (draft-and-wait, per-push approval). **`deep-fix` is an action-shape selector, not a rung on this ladder** — it sits orthogonal to the chain above. Any flag that forbids editing or committing (`dry-run`, `no-edit`, `strict`, `no-commit`) DECLINES the `deep-fix` ROUTING, with a one-line reason, and the named thread falls through to its normal Phase 3/3b classification instead — the invocation is not aborted and no other thread in the cycle is affected — because `/research-implement-review-report` cannot run its research → plan → implement → review arc without editing and committing. `no-reply` still allows the run and only suppresses the reply at the end, exactly as it does for every other path today.
- **Push requires its own explicit, per-push go-ahead — commit does not.** Committing is eager and automatic (above); `git push` is not, and needs an explicit go-ahead from the user for THAT push, given in the current turn. A prior cycle's approval does NOT carry forward — re-confirm for every new push. Counts as approval: "push", "you can push", "push and reply", or an equally explicit instruction naming the push action. Does NOT count: a bare "continue"/"ok" carried over from unrelated context, or any inferred/assumed consent — ask if unsure. This gate applies only to the default path where commits are happening — `no-commit` already skips commit and push entirely and is unaffected. **Unless `auto-push` is set for this invocation, in which case push proceeds automatically once every thread in the cycle has been committed (and replied to, unless `no-reply` is set) — no separate go-ahead is asked for THIS invocation.** `auto-push` is scoped to a single invocation/cycle; a later invocation without the flag reverts to the default gated behavior. See Phase 4.
- **`deep-fix` names exactly one thread per invocation.** `/research-implement-review-report` is a full research → plan → sign-off → implement → review-loop → report arc with a blocking human gate partway through; running it for several threads inside one cycle is not supported, and concurrent single-commit squashes on one branch would collide. Re-invoke the skill to route a different thread.
- **`deep-fix` is incompatible with `loop`.** A polling monitor cannot sit on a blocking human sign-off gate for an unattended interval. If both are passed on the same invocation, STOP and ask the user which was intended rather than guessing.

## Autonomy

The `autonomous` flag (default off) grants the agent full autonomy over every decision this skill itself owns: implementation approach, replies, and push. It is safe to grant fully because this skill was never a substitute for the human's own approval — a human reviewer still reviews and approves the PR before merge regardless of this flag, and that remains the real, external approval gate. `autonomous` only removes THIS SKILL's own internal pause-and-wait checkpoints; it cannot and does not attempt to grant PR approval. Thread resolution is not a separate gate `autonomous` bypasses — it always follows automatically, `autonomous` or not, once a fix's push has landed (see Phase 4), scoped strictly to the threads this skill itself fixed. See the flag-precedence order in Rules for how `autonomous` ranks against `strict`/`no-edit`/`dry-run`/`no-reply`. Two buckets, split deliberately so scope is unambiguous:

### Bucket A — human-decision gates `autonomous` bypasses

`autonomous` bypasses every draft-and-wait-for-confirmation checkpoint this skill would otherwise pause at, in any phase — the gates below are the ones affected in practice; anything in Bucket B is never bypassed regardless.

With `autonomous` set, the agent decides and proceeds instead of drafting/waiting, on these gates:

- **`[ToFix]` Medium/Large** — instead of "prepare the diff in chat, wait" (Phase 3 / `tag-actions.md`): implement directly, using its own judgement for the approach. Note in the reply which approach was chosen and why, in one line.
- **`[Suggestion]` / `[Optional]` non-trivial** — instead of drafting the trade-off and waiting: pick a direction, implement it, and state the chosen direction plus a one-line reason in the reply — posted as an implemented, non-draft reply (not the Draft template Phase 3 otherwise maps non-trivial Suggestions to).
- **`[Question]`** — instead of "never post without an explicit human go-ahead" (`tag-actions.md`): post the answer directly, still meeting the existing draft format's quality bar (claim + reasoning + citation to file:line / test / doc). Flag in the per-cycle report (Phase 5) that a Question reply was posted autonomously — authorship risk is real, and the human should still see that it happened.
- **`[ToDiscuss]`** — instead of "never post a thread reply automatically, surface to human": post a measured reply that frames the options and tags uncertainty. Never implement a CODE change purely off a `[ToDiscuss]` thread, `autonomous` or not — the flag changes who can post the conversational reply, not what the tag authorizes.
- **Automated-review findings that trip Phase 3b's obviousness test's rewrite-from-scratch exception** — instead of falling through to draft-and-ping: the agent proceeds to implement using its own judgement anyway, applying the same "state the reasoning in the reply" discipline. This covers only that residual rewrite-magnitude case: `autonomous` is not needed for a multi-file fix, a schema-threading fix, or a `medium`/`low`-confidence fix, because Phase 3b step 5 implements all of those by default (with the question stated in the reply). Verdicts `needs-clarification` / `false-positive` / `not-applicable` still never implement anything, `autonomous` or not — there's no actionable fix available at all in those cases.
- **The per-push approval gate** — bypassed, same effect as `auto-push`. `autonomous` implies `auto-push`'s behavior (reply → push proceed automatically within the cycle); the user does not need to also pass `auto-push`, though doing so is harmless and redundant.

### Bucket B — structural safety rules `autonomous` never bypasses

These aren't approval gates being withheld out of extra caution — they're either hard safety invariants, another tool's own contract this skill must respect, or a live real-time instruction, and no flag changes any of them. Bucket A, by contrast, holds this skill's OWN approval checkpoints — decisions this skill itself would otherwise pause on:

- Never `git add -A` / `git add .` — explicit paths only.
- Never amend, rebase, or squash existing history; never force-push; never push to any branch other than the PR source branch.
- **`[OutOfScope]` issue field decisions (title, type, labels)** — the human-confirmation step before Task Composer's `mode: create` always runs, `autonomous` or not (Task Composer's own pre-flight contract requires explicit user confirmation plus `owner`/`repo` — see `dev-essentials:task-composer`).
- Never call `mcp__plugin_github_github__issue_write` directly — `[OutOfScope]` tracking always goes through Task Composer's `mode: create` flow.
- Never touch code unrelated to the reviewer's comment (PR-scope discipline).
- Never defer reviewer-stated work to a follow-up issue without the reviewer's own explicit `[OutOfScope]` tag.
- Stalemate detection stays active — stop replying automatically after 3+ exchanges show unresolved disagreement, and surface to the human.
- **A thread is only ever resolved via MCP once THIS skill itself has committed, replied to, AND pushed its fix, `autonomous` or not** — resolution never fires off the ancestry check alone, and never applies to a thread this skill did not fix (see Phase 4). `unresolve_thread` is never called unless the user explicitly asks to reopen a thread.
- **An active "pause for my review" block (or equivalent) still outranks `autonomous` and `auto-push`** — see the flag-precedence order in Rules.
- **`autonomous` never bypasses `/research-implement-review-report`'s own Phase 1 sign-off gate on a `deep-fix` run.** That command states plainly this gate is the point of its Phase 1 — it is another tool's own contract this skill must respect, the same rationale Task Composer's pre-flight confirmation already relies on above.

## Workflow

### Phase 1 — Session bootstrap (once per `/loop` session)

1. Confirm `mcp__plugin_github_github__*` availability. If missing, stop and ask the user to reconnect via `/mcp`.
2. If `deep-fix` and `loop` are both set on this invocation, STOP and ask the user which was intended (see Rules) — do not guess and do not silently drop either flag.
3. Resolve the target PR:
   - `pr` is a full GitHub URL → parse `owner`, `repo`, `pullRequestNumber` from the URL. Verify by calling `mcp__plugin_github_github__pull_request_read` with those values.
   - `pr` is an integer → require `owner` and `repo` params; call `mcp__plugin_github_github__pull_request_read(owner, repo, pullRequestNumber)`.
   - If `owner` or `repo` is missing and cannot be parsed from a URL, STOP and ask the user before making any call. Never infer from git remote or session context.
4. Hydrate PR metadata from the `pull_request_read` response: `title`, `state`, `headRefName`, `baseRefName`, `html_url`, `number`.
5. Initialize an in-memory `processedCommentIds` set (see [references/thread-state-schema.md](references/thread-state-schema.md)).
6. Print a one-line session header reporting the PR number, title, resolved `interval`, and monitoring mode (`one-shot` or `loop <interval>`).

### Phase 2 — Fetch and classify (every cycle)

**Fetch review comments** using `mcp__plugin_github_github__pull_request_read` with `method: get_review_comments`, which returns the PR's review threads WITH per-thread `isResolved`, `isOutdated`, and `isCollapsed` metadata (confirmed fields on this tool's schema) alongside each thread's own node ID (needed later for `resolve_thread`/`unresolve_thread` — distinct from individual comment IDs) and its comments. For PRs with many threads, paginate with `perPage` (max 100) and the cursor-based `after` param per `dev-essentials:github-mcp-conventions` Rule 3 — this method uses cursor pagination (`after` = previous page's `endCursor`), not page numbers.

**Pre-filter noise BEFORE classifying:**

1. Skip any comment authored by a bot not in the user-configured list. Default bot list: `["github-actions[bot]", "copilot[bot]", "coderabbitai[bot]"]`. The user may extend this list via the `bots` param. Bot comments routed through the automated-review path (Phase 3b) are an exception — they are still processed there.
2. **Filter by real thread state.** Skip any thread where `isResolved: true` OR `isOutdated: true`, unless `include-resolved` is set. This is a real status check against GitHub's own field, not a heuristic — do this BEFORE spending any classification effort on the thread, so an already-resolved or stale-diff-position thread never costs a reply. `isOutdated` means the thread's original diff position no longer exists in the current diff (later commits moved past it); its underlying comment may still be technically unresolved, but the code context it was anchored to is gone, so it is skipped by default the same as a resolved thread.
3. Build an in-memory **active roster**: `{id, threadNodeId, isResolved, isOutdated, state, commentCount, lastAuthor, lastContent, filePath, line, html_url}` per surviving thread — `threadNodeId` is required later by Phase 4's resolve call.

**Classify each comment:**

4. For each comment NOT in `processedCommentIds`:
   - Check if the comment is Claude's own reply: match `**[AI]**` or `**[AI][Draft]**` (bold form) or `[AI]` / `[AI][Draft]` (legacy plain form) at the start of the comment body. If matched, skip — do NOT classify.
   - If the comment contains an automated review header (`AI Code Review`, `copilot:review`, or similar bot-generated heading as the first non-empty line) → route to Phase 3b.
   - Otherwise parse leading tags (brackets at the very start, e.g. `[ToFix][Performance]`). Multiple tags combine.
   - No recognizable tag → treat as `[Note]`.
   - If `tags` param is set and no parsed tag intersects it → skip (do NOT add to `processedCommentIds`).

5. **Re-derive committed-fix state for each active thread — no persisted state, re-checked every cycle.** For every thread in the active roster, scan its comment history (already fetched above) for the newest Claude-authored reply — any `**[AI]**` or `**[AI][Draft]**` form (bold or legacy plain) — that makes an **affirmative commit claim**: the phrase "Committed as `<sha>`" or "commit `<sha>`" adjacent to the fix summary. This is a tightened match, not a loose prefix match — it must NOT match the `no-commit` reply template's "Diff staged locally, awaiting your commit." phrasing, which reports an edit but explicitly does NOT claim a commit.

   - Positive match example: `**[AI]** Fixed: renamed FooID → FooId. Committed as a1b2c3d; will be included in the next push.`
   - Negative match example (do NOT treat as committed — no SHA to check, nothing was committed): `**[AI]** Fixed: <summary>. Diff staged locally, awaiting your commit.`

   Four possible outcomes (see [references/thread-state-schema.md](references/thread-state-schema.md) for the matching conventions):

   - **`fresh-unhandled`** — no Claude-authored `**[AI]**`/`**[AI][Draft]**` reply exists at all. Proceed to Phase 3 normally.
   - **`already-assessed`** — the newest such reply is NOT an affirmative commit claim (a `**[AI][Draft]**`, a `Tracked as issue #<id>`, a `[Note]`/out-of-scope acknowledgement, or any other non-draft reply that never claimed a commit). Leave the thread alone, UNLESS a newer human/reviewer reply exists after it (see the guard below) — in that case re-open Phase 3 classification of that newest human reply, exactly as if no prior AI reply existed.
   - **`cured`** — an affirmative commit claim exists and its SHA is already an ancestor of the remote (checked below). Resolve the thread (unless `openFindingsMarker` is set) and report it resolved.
   - **`unconfirmed-commit-claim`** — an affirmative commit claim exists but cannot yet be confirmed safe to report as ready.

   **Guard — check for a newer human/reviewer reply before running any `cured`/`unconfirmed-commit-claim` branch.** This check runs FIRST, before deriving `cured` or `unconfirmed-commit-claim`. Scan the thread's comment history for a reply posted AFTER the newest Claude-authored commit-claim reply that is itself NOT Claude-authored (does not start with `**[AI]**` / `**[AI][Draft]**` or the legacy plain form) — a human/reviewer comment that landed after the AI's last comment. If such a reply exists: do NOT run any catch-up branch automatically for this thread, regardless of what the SHA/ancestry check would otherwise conclude. Report instead: `T#<id> has a newer reply after the AI's last comment — needs human attention before any automated catch-up action.` Then fall through to normal Phase 3 classification of that newest (human) reply. If no such newer reply exists, continue below.

   - Extract a commit SHA from the reply text if the phrasing resolves to one cleanly (e.g. "Committed as `<sha>`", "commit `<sha>`" — do not require an exact template match).
   - Run the ancestry check (see [references/thread-state-schema.md](references/thread-state-schema.md) § "Ancestry check") for that SHA against `origin/<headRefName>` — the PR's own source branch, already cached from Phase 1.

   **Reporting-mode split — applies to both outcomes below, stated once:** if neither `dry-run` nor `no-reply` is set → take the outcome's default action. If `no-reply` is set → skip the interactive prompt and instead print the outcome's report line for the human to handle manually. If `dry-run` is set → print that same report line, with no prompt.

   - **`cured`** (SHA resolves locally and is an ancestor of `origin/<headRefName>`) — the fix has already landed on the remote, from an earlier cycle's or invocation's push, but a prior resolve attempt is either missing or failed (this is the catch-up path — normally a resolved thread would already have been filtered out by Phase 2's `isResolved` pre-filter before reaching here). Always derive this state. If `openFindingsMarker` is `true` for this thread (see [references/thread-state-schema.md](references/thread-state-schema.md)), do NOT resolve — report `T#<id> cured (open findings) — left open.` Otherwise call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` and `threadId: <threadNodeId>` from the roster (resolving an already-resolved thread is a documented no-op on this tool, so a stale roster entry is harmless). On success, report: `T#<id> resolved — <file>:<line>, commit <sha>.` On an MCP error, fall back to: `T#<id> cured — <file>:<line>, commit <sha> — resolve failed (<short reason>), resolve manually via GitHub UI.`
   - **`unconfirmed-commit-claim`** (SHA resolves locally but isn't yet an ancestor of the remote, OR doesn't resolve to a known commit in this checkout at all, OR the reply mentions a committed fix without a SHA that resolves cleanly) — the committed-fix reply cannot yet be confirmed safe to report as ready. Do NOT silently treat the thread as fresh or unhandled, and do NOT implement anything new on it. **There is no `autonomous` bypass for this outcome at all** — an unconfirmed SHA state needs human input regardless of `autonomous`. Report: `T#<id> already has an AI reply about a committed fix (commit <sha-or-"unspecified">) that can't be confirmed safe to report as ready — <hasn't landed on the remote yet | this checkout can't resolve the SHA locally | no SHA could be extracted from the reply>.` Leave the thread untouched until the user responds.

   See [references/thread-state-schema.md](references/thread-state-schema.md) for the reply-text matching conventions this step uses.

### Phase 3 — Act per tag

Apply the matrix in [references/tag-actions.md](references/tag-actions.md). Short summary:

Reviewer-facing tags are written as Markdown bold at the very start of the comment (e.g. `**[ToFix]**`). Match the same convention when referencing them in replies.

| Tag                                                 | Action                                                                                                                                                                                                                         |
|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `**[ToFix]**` / `**[Performance]**` / `**[PX]**`    | Small diff (< ~20 LoC, single file, no public API change) → implement, commit (eager, Phase 4), reply immediately referencing the local SHA. Push is separate, gated by approval. Larger → draft diff in chat, wait for approval — or, if `deep-fix=<threadId>` names this thread, route it through `/research-implement-review-report` instead (see the `deep-fix` override below). |
| `**[Suggestion]**` / `**[Optional]**`               | Trivial → implement like `**[ToFix]**`. Otherwise → draft trade-off in chat, wait. Reply language respects the "optional" nature.                                                                                              |
| `**[Question]**`                                    | Draft the answer in chat, show it to the user, and post the `**[AI][Draft]**` reply ONLY after explicit user confirmation. Never post without confirmation.                                                                    |
| `**[ToDiscuss]**`                                   | Never implement. Summarize positions in chat and ask the user whether to draft a reply. Do NOT post a thread reply without that confirmation.                                                                                  |
| `**[OutOfScope]**`                                  | Never implement in this PR. If tracking requested → delegate to **Task Composer** agent to draft the issue; confirm with user; only then create the GitHub issue via `mcp__plugin_github_github__issue_write`. Reply `**[AI]** Tracked as issue #<id>`. |
| `**[Note]**` (and untagged)                         | Summarize in chat. No thread reply, no code edit, unless the human asks.                                                                                                                                                       |
| `**[Repetition]**`                                  | Handle as the underlying tag but ALSO surface the pattern: "Apply pattern fix across all N occurrences?"                                                                                                                       |
| Automated review header                             | Run Phase 3b. `valid`/`valid-but-narrow` findings that pass the obviousness test act like `[ToFix]` and are implemented directly — size and file count are not disqualifiers, and less-than-high confidence means "ask the question in the reply AND still fix it". Only a rewrite-from-scratch-magnitude redesign, or a `needs-clarification`/`false-positive`/`not-applicable` verdict, drafts and waits. |

The "small vs. large" cut-off is **your judgement call**, not a hard rule — ~20 LoC / single file / no public API change is only a guideline (this cut-off governs `[ToFix]`/`[Performance]`/`[PX]`/trivial `[Suggestion]`; it does not govern the automated-review path — see Phase 3b step 5). Per-thread overrides from the reviewer always take precedence:

- **"Just fix it" / "no draft, apply directly"** in the thread (or in chat) → implement and commit even if you'd normally draft, provided the reviewer's intent is unambiguous.
- **"Show me a draft first" / "don't commit yet" / "let me see the diff"** → switch to draft-only for that thread even if the change is trivial. Post `**[AI][Draft]**` and wait.

When applying either override, mention it in the reply so the trail is explicit.

#### `deep-fix` override

When the invocation's `deep-fix=<threadId>` (or `T#<threadId>`) names THIS thread, and the thread is eligible (below), it does NOT take its normal per-tag action from the matrix above — it is routed to the **Deep-fix dispatch** (Phase 4) instead, after Phase 3b if the thread is an automated-review finding (see Phase 3b step 5's second exit). `deep-fix` names exactly one thread per invocation (see Rules); a human naming the thread is itself the eligibility signal — there is no size or tag whitelist beyond the hard ineligibility list below.

**Hard ineligibility — decline the `deep-fix` ROUTING with a one-line reason, and fall through to normal Phase 3/3b classification instead:**

| Refused                                                                 | Why                                                                                                                                                                     |
|--------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Automated-review `needs-clarification` / `false-positive` / `not-applicable` | No actionable fix exists at all — Phase 3b step 5 / `automated-review-verification.md`'s hard rules never implement anything for these verdicts.                       |
| `**[ToDiscuss]**`                                                        | Never implement a code change purely off a `[ToDiscuss]` thread (§ Autonomy, Bucket A — `autonomous` or not).                                                          |
| `**[OutOfScope]**`                                                       | Never implement in this PR (Phase 3 matrix; § Autonomy, Bucket B).                                                                                                      |
| `**[Question]**` / `**[Note]**` / untagged                               | No code change is authorized on these tags at all.                                                                                                                      |
| `unconfirmed-commit-claim`                                                | No `autonomous` bypass exists for this outcome; nothing new is implemented on it (Phase 2 step 5).                                                                     |
| `cured` or `already-assessed` (no newer human reply)                     | Already terminal; `deep-fix` does not re-open a settled thread.                                                                                                         |
| A fix that would reach outside the current PR's diff                     | PR-scope discipline — no flag bypasses it (§ Autonomy, Bucket B).                                                                                                       |
| `dry-run`, `no-edit`, `strict`, or `no-commit` set for this invocation   | These already forbid editing/committing, and `/research-implement-review-report` cannot run its arc without both — see the Rules flag-precedence clause.               |

### Phase 3b — Automated review verification

Automated review comments are frequently too narrow, false-positive, or not applicable to production paths. Always verify independently before replying. Full checklist, verdict enum, and draft examples in [references/automated-review-verification.md](references/automated-review-verification.md).

Minimum steps:

1. Read the actual code at the thread's file path and line range. Do not trust the quoted snippet.
2. Widen the lens: enclosing method, callers, relevant tests, DI composition, feature-flag guards.
3. Decide verdict: `valid`, `valid-but-narrow`, `needs-clarification`, `false-positive`, or `not-applicable`.
4. Assign confidence: `high` / `medium` / `low`.
5. **Obviousness test — only for `valid` / `valid-but-narrow` verdicts.** `needs-clarification`, `false-positive`, and `not-applicable` are NEVER eligible for this path, regardless of size — skip straight to step 6 for those.

   For `valid` / `valid-but-narrow`, the question is **not how big the fix is**. It is one question: **would the right fix mean rewriting the target file or section from scratch, or a redesign of equivalent magnitude?** If no, it is a fix — implement it. Check all three conditions:

   - **It is a fix, not a ground-up redesign.** Line count, file count, and "it touches more than one place" are explicitly **not** disqualifiers. A multi-file fix, threading a field through a schema and its consumers, tightening a rule the code or the doc already states, adding a missing case to logic that already exists, and resolving a self-contradiction between two parts of the current change **all qualify as fixes**. Only the rewrite-from-scratch exception below disqualifies.
   - **It stays entirely within files/areas already touched by the current PR's diff** — no expansion into new out-of-scope files or areas. This is PR-scope discipline, a structural rule no flag bypasses (§ Autonomy, Bucket B).
   - **It does not introduce a NEW architecture or a NEW public contract.** Making documented behavior match reality, tightening an already-stated rule, closing a gap in already-existing logic, or correcting a stated-vs-actual mismatch is **not** an architecture or contract change — it is a fix to one that already exists. Only introducing a mechanism or contract that is not there today trips this.

   **The exception — the only case that declines direct implementation.** Fall through to step 6 ONLY when the right fix would mean rewriting the target file or section from scratch, or an equivalently fundamental redesign. Both halves must hold: (a) the reviewer is asking for a fundamentally different mechanism with **no precedent anywhere in this codebase** to follow, AND (b) there are **multiple materially different ways to build it** with nothing in the existing code to choose between them. Examples that DO still warrant drafting: "replace the whole polling design with an event-driven one" in a codebase with no event infrastructure; "split this into three separate commands" where the split boundary is genuinely undecided. Nothing in the first condition's list reaches this bar.

   **Second exit from this fall-through: `deep-fix`.** When `deep-fix=<threadId>` (or `T#<threadId>`) names this thread, the exception's fall-through routes to the **Deep-fix dispatch** (Phase 4; see also Phase 3's `deep-fix` override) instead of step 6 — a rewrite-from-scratch-magnitude finding is precisely the case `/research-implement-review-report` exists to work: research the precedent, surface the design choice for sign-off, implement, review. `needs-clarification` / `false-positive` / `not-applicable` verdicts remain ineligible for `deep-fix` regardless of this exit — see Phase 3's ineligibility table.

   **Confidence is not a gate — it changes what you SAY, not what you DO.** With `confidence: high`, implement and reply as below. With `medium` or `low` — or whenever you are uncertain about the RIGHT approach rather than about whether to fix at all — **still implement your best-judgment fix**, and additionally state the uncertainty as an explicit question in the chat report and in the thread reply: `Implemented <X>. Open question: <the specific choice you made and the alternative>. Say the word and I'll switch.` Asking and fixing are not alternatives — **ask AND fix**. The only thing that stops the fix is the rewrite-from-scratch exception above. (Do not confuse this with the `needs-clarification` verdict, which is about whether there is a defect at all — that verdict is still never implemented.)

   Conditions hold → treat exactly like `[ToFix]`: implement, commit (Phase 4), and post a non-draft `**[AI]**` "Implemented fix" reply (see the reply templates below) — skip the draft/ping-approval steps entirely for this thread; there is no draft stage on this path. The exception applies → continue to step 6.
6. Post `**[AI][Draft]**` reply using one of the verdict templates in `references/automated-review-verification.md`. Every template ends with `*Draft pending author confirmation.*` — include this closing line.
7. Ping the human in chat. Do NOT edit code. Wait for approval before implementing.

### Phase 4 — Commit, reply, push, then flag for resolution

Reply happens right after commit, before push, so the reply text never overclaims: it reports what is locally committed, not what a reviewer can already see. Resolving a thread is a different kind of claim — it tells a human reviewer the fix is visible to them, which isn't true until the push has actually landed. `mcp__plugin_github_github__pull_request_review_write`'s `resolve_thread` method (confirmed on this MCP server's tool surface: `threadId` in, no `owner`/`repo`/`pullNumber` needed, resolving an already-resolved thread is a documented no-op) is what makes that claim true, so this skill calls it itself, but ONLY after the push that makes it true has actually landed — never before. Push itself is gated by an explicit, per-push user approval (see Rules; unless `auto-push`/`autonomous` is set) and happens once per cycle, after every thread below has been verified, committed, and replied to.

For every thread being fixed this cycle, do the following in order before moving to the next thread:

**Exception when `squash` is set:** steps 1–2 (verify, stage) still run per thread inside this loop, but step 3's single commit does not exist until the end of the cycle (see the `squash` bullet under step 3) — so step 4's reply cannot reference a per-thread SHA yet. Run steps 1–2 for every thread first, create the single end-of-cycle commit, THEN loop back and run step 4 for every thread, each reply referencing that one shared SHA, before moving on to push.

**Exception when `deep-fix=<threadId>` names a thread eligible per Phase 3's `deep-fix` override:** that thread does NOT run steps 1–4 in this per-thread loop. It runs the **Deep-fix dispatch** below LAST in the cycle — after every other thread's steps 1–4 above (including a `squash`-bundle commit, if `squash` is also set) and BEFORE the cycle's single push. This ordering guarantees nothing else commits on the branch between the `HEAD` the dispatch records and the single commit it produces.

1. **Verify** — build the affected project(s) and run the affected tests. Do NOT commit if the build fails or any test regresses.
2. **Stage** — `git add` only the files touched by this specific thread. Never `git add -A` / `git add .`.
3. **Commit** — create one commit per thread (default). A local `git commit` produces a real SHA the moment it succeeds — BEFORE any push exists. Message format:

   ```text
   PR #<prId> T#<commentId>: <short imperative summary>

   <1-3 lines explaining *why*, referencing the reviewer's point>

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   - If `squash` is set → do NOT interleave with step 4 per thread (see the exception noted above). Accumulate all fixes from every thread's steps 1–2 first, then create ONE commit at the end of the cycle with all `T#<id>` references listed in the body — only then move on to step 4 for each thread.
   - If `no-commit` is set → skip commit + push entirely; leave edits staged for the human, and reply with the "staged" template below.
   - **Do NOT ask the user for commit approval.** Commit stays eager and automatic — that default is unchanged. (Push is different — see below.) If the user gave feedback on a previous cycle ("LGTM, proceed"), that does NOT reset the commit default to `no-commit`. If the user wants to inspect before committing, they say so explicitly with the `no-commit` flag.

4. **Reply** via `mcp__plugin_github_github__add_reply_to_pull_request_comment` using the templates below, referencing the LOCAL commit SHA created in step 3 — the reply does not claim the fix has been pushed. This reply is itself the durable record of the commit — no separate persisted state is written or needed. A later cycle's Phase 2 step 5 re-derives the committed-but-unpushed state directly from this reply text plus `git merge-base --is-ancestor` against the remote, whether that later cycle runs in this same invocation or a future one. Repeat steps 1–4 for every thread being fixed this cycle before moving on to push.

**Push — once per cycle, after steps 1–4 above have run for every thread in the cycle:** gated by an explicit, current-turn user go-ahead (see Rules; a prior cycle's approval does not carry forward) — unless `auto-push`/`autonomous` is set, in which case proceed directly to push once all threads in the cycle are committed (and replied to, unless `no-reply` is set). `git push` once for the whole cycle's commits — this holds whether they were one-per-thread or bundled via `squash`; either way, exactly one push per cycle. Never force-push. Never push to a protected branch other than the current PR source branch. If approval hasn't arrived by the time the cycle log is printed, leave the commits unpushed and say so explicitly in Phase 5 (`N commits ready, not yet pushed — push when ready`) — the replies already posted stay accurate, since they only ever claimed a commit, never a push; no thread from this cycle is resolved until the push actually lands (see "Resolve threads and report" below). **Exception:** if this cycle ran a `deep-fix` thread and it ended `stop-blocked`, this cycle's push is cancelled entirely — not just for that thread — see "Deep-fix dispatch" below.

**Resolve threads and report — runs after this cycle's push succeeds, for (a) the threads this cycle just committed and replied to, AND (b) any thread Phase 2 step 5 flagged this cycle as `unconfirmed-commit-claim`:** once `git push` succeeds:

- For each thread committed and replied to in steps 1–4 above this cycle (and NOT carrying `openFindingsMarker: true` — see the Deep-fix outcomes below), run the ancestry check (see [references/thread-state-schema.md](references/thread-state-schema.md) § "Ancestry check") for that commit's SHA against `<pushed-tip>` — the just-pushed commit/branch state this cycle's own push produced, not the remote-tracking ref. Success (expected, since the push just carried that commit) → call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` and `threadId: <threadNodeId>` from the Phase 2 roster. On success, report the thread resolved: `T#<id> resolved — <file>:<line>, commit <sha> pushed as part of this cycle.` On an MCP error, report instead: `T#<id> pushed but resolve failed (<short reason>) — resolve manually via GitHub UI.` Failure of the ancestry check itself → the commit isn't actually on the pushed branch (e.g. dropped, rebased away) → do NOT call resolve; report the thread as still open; do not guess. A thread with `openFindingsMarker: true` is never resolved here — see "Deep-fix dispatch" below.
- For each thread Phase 2 step 5 flagged this cycle as `unconfirmed-commit-claim`, re-run the same ancestry check against `<pushed-tip>` when a SHA exists to check; for the sub-case where no SHA cleanly resolved at all, there is nothing to re-check. If it now succeeds, resolve and report the same way. If it still fails, leave the report as-is — a later cycle's Phase 2 step 5 will keep re-checking it.

Threads carried over from an EARLIER cycle or invocation — where a fix was committed and replied to, but that cycle ended before its push happened — are NOT tracked here via any persisted state. Instead, Phase 2 step 5 re-derives that state directly at the top of every cycle: it re-reads each active thread's existing `**[AI]** Fixed: ... Committed as <sha>` reply (already part of the thread's comment history fetched in Phase 2) and runs the ancestry check against `origin/<headRefName>`. If that check now succeeds (an earlier cycle's later push already landed it), Phase 2 resolves the thread as a catch-up step. If it doesn't yet succeed, Phase 2 surfaces it to the user instead of silently reprocessing it — there is no `autonomous` bypass for this outcome. Note that in normal operation this catch-up path fires rarely: once a resolve call succeeds, the thread's `isResolved` flips true on GitHub itself, and Phase 2's pre-filter (see Phase 2 step 2) skips it on every later fetch before step 5 ever runs — the catch-up path exists mainly for a failed resolve call or a reply posted before this skill supported resolving. This re-derivation is simpler and inherently correct across sessions/invocations — it depends on GitHub's own thread history and real git ancestry, not on any file surviving between runs.

If push approval doesn't arrive this cycle (or the push fails), no thread from this cycle is resolved — leave them open, with the reply already posted; a later cycle's Phase 2 step 5 (or a retry of this same push) will find the reply and resolve it once the push actually lands (Phase 5's cycle log already carries the unpushed state as `N commits ready, not yet pushed — push when ready`).

Splitting commits when one file covers multiple threads:

- For files touched by more than one thread, reset the file to `HEAD` after capturing the final state, then re-apply each thread's edit and commit it before moving to the next.

Bundle threads that share one pattern:

- When three-plus threads carry the **same reviewer note** applied at different call sites, treat them as one logical fix with one commit and reply on each thread pointing at the shared SHA.

#### Deep-fix dispatch — brief and outcomes

**Pre-flight — establish the checkout root before running anything.** Resolve the local checkout root with `git rev-parse --show-toplevel`, then confirm `git rev-parse --abbrev-ref HEAD` in that root equals the PR's `headRefName` (Phase 2 step 5 deliberately does not assume it does). If either check fails or disagrees, STOP and ask the user before checking out, switching, or creating anything.

**Invocation.** Run `/research-implement-review-report` as this skill's own next step, in the SAME session — never delegate it to a subagent, because it must hold that command's own Phase 1 sign-off gate, which a one-shot dispatch cannot be asked a follow-up question to satisfy. Pass:

1. The **branch name** (the PR's `headRefName`) and the **absolute worktree path** — the two facts that command's own pre-existing-branch verification step needs.
2. `--base=<baseRefName>` — the PR's own target branch, already cached from Phase 1.
3. `--commit-mode=single` and `--rounds=<deep-fix-rounds>`.
4. **Commit-subject override** — the single squash commit MUST use this skill's own Phase 4 step 3 format: `PR #<prId> T#<threadId>: <subject>`, body explaining *why* and referencing the reviewer's point, the `Co-Authored-By` trailer.
5. **Squash-window exclusivity** — no other commit will land on this branch between the recorded `HEAD` and the squash (see the ordering rule above). If that command's own squash-base safety stop trips anyway, let it stop and report — do not override it.
6. **Scope guard** — the fix stays inside files/areas already touched by this PR's diff and addresses only this thread.
7. **Artifact guard** — never stage or commit that command's own research/plan/report artifacts, and never reference their paths in the thread reply or the commit message — pipeline-internal artifacts stay out of anything shipped (`dev-essentials:engineering-discipline` Rule 3).
8. **No push, ever** — this skill owns the single per-cycle push, and `/research-implement-review-report` already never pushes without the user's own explicit go-ahead.
9. Expect back: the squash SHA, the review-loop stop verdict (`stop-clean` / `stop-max-rounds` / `stop-blocked`), the round count, and the deferred-findings list.

**Reply, by stop verdict:**

| Verdict           | Commit?               | Tree  | Reply                                                           | Resolved after push?          |
|--------------------|------------------------|-------|-------------------------------------------------------------------|-----------------------------------------------|
| `stop-clean`       | yes (one squash SHA)  | green | "Implemented fix" template + one clause naming the arc            | Yes — normal eligibility rule above           |
| `stop-max-rounds`  | yes                    | green | "Implemented fix" template + an explicit outstanding-work line    | No — left open, `openFindingsMarker: true`    |
| `stop-blocked`     | no (nothing kept)     | red   | nothing posted by default — STOP and ask the user                 | No                                             |

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

Both are affirmative commit claims by the existing "Committed as `<sha>`" match, so Phase 2 step 5 and this phase's resolve-and-report step keep working unchanged without any new state machine. The `stop-max-rounds` reply's closing sentence STARTS WITH the `openFindingsMarker` marker phrase a later cycle matches on — a prefix match on `Open findings remain; leaving this thread open`, punctuation-agnostic; see [references/thread-state-schema.md](references/thread-state-schema.md).

Never link that command's own report artifact from either reply — it is a pipeline-internal artifact (`dev-essentials:engineering-discipline` Rule 3); the reply summarizes the arc, round count, and verdict instead.

**`stop-blocked` — cancel the cycle's push.** `/research-implement-review-report`'s `--commit-mode=single` will already have made review-loop's per-round commits on the PR's source branch before it can know the build is red — step 1's "do NOT commit if the build fails" rule cannot prevent commits that already happened inside that command's own arc. So: do NOT squash, do NOT post a `**[AI]**` "Fixed" reply, and do NOT post `**[AI][Draft]**` either — `automated-review-verification.md` reserves that prefix for a proposal, and a half-finished commit stack is not a proposal. **Cancel this cycle's push entirely** (every thread's commits, not just this one) and STOP: report to the user that red commits already sit on the PR source branch and pushing would publish a broken PR. Report it in Phase 5 as `deep-fix — blocked (build red, not pushed)`, and offer the two real recovery options: fix forward in this session, or reset the branch back to the pre-dispatch SHA (a new commit / `git reset` on this **unpushed** tip only — Bucket B still forbids amending or rewriting *pushed* history).

#### Reply templates and thread resolution

Every reply starts with a **leading tag section** — the `**[AI]**` (or `**[AI][Draft]**`) marker, optionally followed by other bold reviewer-style tags, and closed with a bold `**[T#<commentId>]**` thread tag rendered as a clickable deep link — all on the FIRST line.

**Link format for the T# tag.** GitHub PR review comment URLs use the `html_url` field returned by `pull_request_read`. Use that field directly — do NOT construct the URL manually (see `dev-essentials:github-mcp-conventions` §Thread anchors).

```markdown
**[[T#<commentId>](<html_url>)]**
```

Tag order on the first line:

```text
**[AI]** [optional auxiliary tags] **[[T#<commentId>](<html_url>)]**
<blank line>
<body>
```

Reply templates:

- Implemented fix (committed locally; push is a separate, later, gated step) → `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nFixed: <one-line summary>. Committed as <short-sha>; will be included in the next push.`
- Implemented fix with `no-commit` → `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nFixed: <one-line summary>. Diff staged locally, awaiting your commit.`
- Issue created → `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nTracked as issue #<id>: <title>.`
- Draft (automated review / Question / non-trivial Suggestion) → `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**\n\n<analysis>\n\n*Draft pending author confirmation.*`
- Optional suggestion declined or deferred → `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**\n\nOptional — keeping current shape; happy to change if preferred. Reason: <one line>.`
- Override applied ("just fix it") → first line stays `**[AI]** **[[T#<commentId>](<html_url>)]**`; body starts with `Per your "just fix it" direction: …` so the waiver is traceable.
- Override applied ("draft first") → first line stays `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**`; body starts with `Draft per your request: …`.

Cross-thread references inside the body should use the same linked form — resolve the target comment's `html_url` from the Phase 2 roster. Never hand-build URLs.

Reply style rules (from [references/review-principles.md](references/review-principles.md)):

- Frame as a request or statement of fact, not a command.
- Prefer "we" over "you".
- Tie judgement to a principle (SRP, naming, perf budget, invariant) rather than preference.
- Keep replies to ≤ 3 short lines unless the reviewer asked for depth.

**Thread resolution is scoped to threads this skill itself fixed.** `mcp__plugin_github_github__pull_request_review_write` (`method: resolve_thread`, taking the thread's node ID) is a real, confirmed tool on this MCP server's surface, and the skill calls it — but ONLY once the eligibility rule above is met (committed, replied to, AND actually pushed), never speculatively and never for a thread it did not itself fix:

- **Resolve** — threads meeting the eligibility rule above where the change demonstrably addresses the reviewer's point (e.g., `[ToFix]`, `[Performance]`, automated-review-derived fixes where coverage was implemented).
- **Never resolve** — false-positive analysis threads (the reviewer reads and resolves at their own pace), `[Note]` / acknowledgement-only threads, automated-review summary banners (never touched at all), out-of-scope items (leave open after the tracking-issue reply), a thread whose fix came from a `deep-fix` run that ended `stop-max-rounds` with outstanding findings (`openFindingsMarker: true` — see "Deep-fix dispatch" above), and any thread that doesn't yet meet the eligibility rule above. `unresolve_thread` is never called at all unless the user explicitly asks to reopen a specific thread.

### Phase 5 — Cycle log

After each cycle, print a compact table to the user:

```text
Cycle 2 @ 15:42 — PR #4421 (5 threads checked, 2 new comments)
  T#9  [ToFix]  Retry.cs:17          → fixed (cycle 1), commit 9f3a1c2       | resolved (this cycle's push landed it)
  T#12 [ToFix]  Auth.cs:42           → fixed (2 LoC), commit a1b2c3d        | reply posted, pending push
  T#17 [AutoReview] Domain/User.cs:88 → verdict: false-positive              | draft posted, awaiting approval
  T#22 [Note]   README.md:3          → noted                                | no action

1 commit ready, not yet pushed — push when ready.
```

`T#12`'s reply is already live, but it is NOT resolved this cycle — that waits for its commit to actually be pushed (see Phase 4). `T#9` illustrates the carried-over-thread mechanic: its fix was committed and replied to back in cycle 1, but cycle 1 ended (one-shot default, Phase 6 rule 1) before that commit got pushed. At the start of cycle 2, Phase 2 step 5 re-read `T#9`'s existing `**[AI]** Fixed: ... Committed as 9f3a1c2` reply, found it was not yet an ancestor of `origin/<headRefName>`, and flagged it `unconfirmed-commit-claim`. Cycle 2's push happened to include commit `9f3a1c2`, so once that push landed, cycle 2's own "Resolve threads and report" step re-ran the ancestry check against `<pushed-tip>`, called `resolve_thread` for `T#9`, and reported it resolved — same cycle as the push, not a later close-out notice. Because the resolve call flips `T#9`'s `isResolved` to `true` on GitHub itself, cycle 3's Phase 2 pre-filter would skip it before it ever reaches the roster — it will not appear in cycle 3's table at all.

With `squash`, replace the per-thread commit SHAs with a single end-of-cycle line: `Cycle commit a1b2c3d (T#12, T#14, T#18).` With `no-commit`, replace the SHA segment with `staged locally`.

Always end the log with an explicit push-status line so it is never ambiguous whether the reviewer can see the fix yet: `N commits ready, not yet pushed — push when ready` when this cycle's commits are still awaiting the user's push approval, or `N commits pushed as <sha(s)>` once approval arrived (or `auto-push`/`autonomous` applied) and the push landed.

A `deep-fix` thread's row uses one of `deep-fix (N rounds, clean)`, `deep-fix — open findings`, or `deep-fix — blocked` in place of the usual `<short outcome>` — see [references/thread-state-schema.md](references/thread-state-schema.md) § "Cycle log" for the full outcome-value list. A cycle whose `deep-fix` run ended `stop-blocked` prints `deep-fix — blocked (build red, not pushed)` in place of the usual push-status line, since that cycle's push was cancelled entirely (see Phase 4's "Deep-fix dispatch" outcomes).

Add a comment ID to `processedCommentIds` only AFTER its action (or explicit skip decision) completes successfully. On failure, leave it unprocessed so the next cycle retries.

### Phase 6 — Loop and pause

Default is **one-shot**; monitoring is opt-in.

1. **No `loop` flag and no outer `/loop` wrapper (default)** → exit after the first cycle. Announce: `Monitoring skipped (one-shot default). Pass 'loop' to start polling.`
2. **Already wrapped in `/loop`** → return control to `/loop`; it performs the sleep and re-invokes. Do NOT start a nested `/loop`.
3. **`loop` flag set on a standalone invocation** → at end of first cycle, auto-enter monitoring:

   ```text
   /loop <interval> /process-pr-comments pr=<id> owner=<owner> repo=<repo> [other original params except 'loop', 'auto-push', 'deep-fix', and 'deep-fix-rounds']
   ```

   Forward every param the user supplied except `loop` (the inner invocation no longer needs it — it runs under `/loop`), `auto-push` (scoped to a single invocation/cycle — see Rules — so it applies only to this first cycle and is dropped from the re-invocation; every later monitor tick reverts to the default gated push behavior), and `deep-fix`/`deep-fix-rounds` (already incompatible with `loop` — see Rules — a polling monitor cannot sit on a blocking sign-off gate unattended, so it is dropped from the re-invocation rather than re-triggered). The `interval` is the resolved value (default `15m`). Announce the transition: `Entering monitor mode: /loop <interval>.`

If the PR transitions to `closed` or `merged` during any cycle, stop the loop and tell the user.

## Stalemate detection

Count `**[AI]**`-prefixed reply + reviewer-response exchange pairs across the thread's full history. If that exchange count exceeds 3 AND the latest two replies show unresolved disagreement, stop replying automatically. Surface the thread to the human: "Consider escalation, a design review, or talking this out synchronously."

## Safeguards

- Do NOT touch code unrelated to the reviewer's comment (respect PR scope).
- Do NOT post replies when `dry-run` or `no-reply` is set.
- Do NOT implement edits when `dry-run`, `no-edit`, or `strict` is set; draft only.
- Do NOT commit or push when `dry-run` or `no-commit` is set.
- **Do NOT push without an explicit, current-turn user go-ahead** (see Rules and Phase 4's "Push" paragraph). Commit is eager and automatic; push is not, and a prior cycle's approval does not carry forward. The sole exception is `auto-push` or `autonomous` (which implies the same bypass) — see the flag-precedence order in Rules for how these rank against an active "pause for my review" instruction, `dry-run`, and `no-commit`.
- **Do NOT resolve a thread before its commit has actually been pushed.** Reply happens early (right after commit, before push); the resolve call happens late — only once that commit's push actually lands, whichever cycle or invocation that happens in — see Phase 4.
- Do NOT amend, rebase, squash existing history, or force-push. Always create fresh commits.
- Do NOT push to any branch other than the PR source branch.
- Do NOT invent issue fields when delegating to Task Composer — always confirm title and type with the user first. This rule is never bypassed, `autonomous` or not — see § Autonomy, Bucket B.
- Do NOT reprocess a comment already in `processedCommentIds` within the same session.
- Do NOT call any GitHub MCP tool with inferred `owner` or `repo` — always pass user-supplied or URL-parsed values verbatim (see `dev-essentials:github-mcp-conventions` Rules 1–2).
- **Do NOT resolve or unresolve any thread this skill did not itself fix, commit, reply to, AND push in this session** — the `resolve_thread` call in Phase 4 is scoped strictly to those threads. Never call `unresolve_thread` unless the user explicitly asks to reopen a specific thread. No flag, including `autonomous`, changes this.
- **Never stage or commit a `deep-fix` run's research/plan/report artifacts, and never reference their paths in a thread reply or commit message** — pipeline-internal artifacts stay out of anything shipped (`dev-essentials:engineering-discipline` Rule 3; see Phase 4's "Deep-fix dispatch" brief).
- **Never push a cycle whose `deep-fix` run ended `stop-blocked`.** Cancel that cycle's push entirely — every thread's commits, not just the `deep-fix` thread's — and STOP; see Phase 4's "Deep-fix dispatch" outcomes.

## Supporting files

| File                                                                                                  | When to read                                                                    |
|-------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [references/tag-actions.md](references/tag-actions.md)                                               | Before acting on any tagged comment — full per-tag matrix with worked examples. |
| [references/review-principles.md](references/review-principles.md)                                   | Before composing replies — distillation applied to the author's side.           |
| [references/automated-review-verification.md](references/automated-review-verification.md)           | Before drafting any `**[AI][Draft]**` reply to an automated review comment.     |
| [references/thread-state-schema.md](references/thread-state-schema.md)                               | When initializing or updating the in-session dedup state and cycle log.         |

## Invocation examples

```text
# One-shot on a specific PR (owner and repo required)
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo

# Full GitHub URL — owner and repo parsed automatically
/process-pr-comments pr=https://github.com/Vasar007/my-repo/pull/42

# Opt in to polling monitor at default 15m cadence
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo loop

# Specific PR, 30-minute polling
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo loop interval=30m

# Dry-run classification only, focus on [ToFix] and [Question]
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo dry-run tags=ToFix,Question

# Strict mode — nothing is edited without approval
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo loop strict

# Edit + stage only, no commit, no push (human will commit)
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo no-commit

# Bundle all fixes from this cycle under a single commit; push still needs your explicit go-ahead
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo squash

# Reply-push in one pass, no separate push approval this invocation
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo auto-push

# Full autonomy: implement, decide, reply, push — no pauses (a human still reviews and approves the PR before merge)
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo autonomous

# Route one Medium/Large [ToFix] thread through research-implement-review-report instead of drafting it
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo deep-fix=T#2201458823

# Same, with a 3-round review loop instead of the default 2
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo deep-fix=2201458823 deep-fix-rounds=3

# Already wrapped in /loop — outer harness controls cadence
/loop 15m /process-pr-comments pr=42 owner=Vasar007 repo=my-repo
```
