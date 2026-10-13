---
name: process-pr-comments
description: "Process GitHub pull-request review comments as the PR author, using the review-tag taxonomy ([ToFix], [Optional], [Suggestion], [Question], [ToDiscuss], [Performance], [OutOfScope], [Note], [PX], [Repetition]) and the special automated-review header. Skips threads GitHub already marks resolved or outdated ('isResolved'/'isOutdated') before classifying anything. Classifies every remaining comment, implements small fixes (including obvious, narrowly-scoped automated-review findings) directly, by default also implements larger fixes whose approach the comment or the code settles, drafts ambiguous ones, re-verifies automated review proposals before replying, delegates issue creation to Task Composer, and posts [AI]-prefixed replies; once a fix's commit is confirmed pushed, the skill resolves that thread itself via GitHub MCP's 'pull_request_review_write' ('method: resolve_thread'). Commit is eager and automatic; push is a separate, explicitly user-gated step (unless 'autonomous' is set) that happens once per cycle, after every thread's reply is posted. Runs once by default; opt in to a polling monitor with the 'loop' flag (default cadence 15m), or route one named thread through '/research-implement-review-report''s research → plan → review cycle with the opt-in 'deep-fix=<threadId>' flag. Triggers on requests like \"process PR comments\", \"work through review feedback\", \"handle GitHub PR comments\", \"respond to reviewers\", \"address review comments\", \"monitor PR for new comments\", or a GitHub PR URL with a request to act on its feedback."
---

# Process PR Review Comments

## Purpose

Acts on review comments **as the PR author**. Before classifying anything, Phase 2 filters out threads GitHub itself already marks `isResolved` or `isOutdated` (real fields returned by `pull_request_read` `get_review_comments` — confirmed in this MCP server's tool schema), so the skill never spends a reply on a dead conversation. Classifies each remaining comment by its review tag, applies a tiered response workflow (implement small fixes, draft larger ones, answer questions, delegate tracking issues), and posts a concise `**[AI]**`-prefixed reply (Markdown bold, matching the reviewer convention of bolding leading tags like `**[ToFix]**`) so reviewers can distinguish Claude's responses from the author's. Once a fix is committed locally, the `**[AI]** Fixed` reply is posted immediately, referencing the local commit SHA — before push. Once that commit's push actually lands (whichever cycle or invocation that happens in — see Phase 2 step 5 and Phase 4), the skill resolves the thread itself by calling `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread` — this MCP server's tool surface does expose thread resolution, contrary to an earlier iteration of this skill's assumption. Pushing is a separate, explicitly user-gated step (unless `autonomous` is set for that invocation) — see Phase 4 — that happens once per cycle, after every thread's fix has been committed and replied to.

## When to use

- User asks to process, work through, or address PR review comments.
- User pastes a GitHub PR URL or a PR number and asks for comment handling.
- User wants a recurring monitor ("every 15 minutes check for new comments").
- Automated review bots (e.g., GitHub Actions, Copilot, CodeRabbit) have commented on the PR and the user wants verified, drafted responses.

## When NOT to use

- Reviewing code written by someone else — that is the reviewer side, handled by other workflows.
- Creating a PR, editing its description, changing reviewers — use `dev-essentials:pr-composer`.
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
| `bots`              | comma-separated bot login names                  | `github-actions[bot]`, `copilot[bot]`, `coderabbitai[bot]` | Extend the default automated-review bot list whose non-automated-review comments Phase 2 step 1 filters out as noise. Comments routed through the automated-review path (Phase 3b) are still processed regardless of this list.                                                                                                                                                                                                                                                                                                       |
| `no-reply`          | flag                                              | off                         | Do not post thread replies; code edits still allowed.                                                                                                                                                                                                                                                                                                                                                                                                     |
| `no-edit`           | flag                                              | off                         | Draft-only; never edit files, even for trivial fixes.                                                                                                                                                                                                                                                                                                                                                                                                     |
| `no-commit`         | flag                                              | off                         | Edit and stage locally only — do NOT commit or push. Useful for review sessions where the human wants to inspect.                                                                                                                                                                                                                                                                                                                                        |
| `squash`            | flag                                              | off                         | Bundle all fixes from this cycle into one commit instead of one commit per thread. Push (once per cycle) is still gated by explicit approval unless `autonomous` is set.                                                                                                                                                                                                                                                                    |
| `autonomous` | flag | off | No gate of this skill stops: Bucket A1, Bucket A2, and the push go-ahead (see § Autonomy). It posts `[Question]`/`[ToDiscuss]` replies, implements fixes where nothing settles the approach, creates `[OutOfScope]` issues through Task Composer, and pushes once per cycle. It keeps the invariants of Bucket B and an active "pause for my review" instruction. `--autonomous` also works. On a `deep-fix` run, pass `--autonomous` to `/research-implement-review-report`. |
| `interactive` | flag | off | Stop at the gates of Bucket A1 and Bucket A2 (see § Autonomy). `--interactive` also works. On a `deep-fix` run, pass `--interactive` to `/research-implement-review-report`. |
| `strict`            | flag                                              | off                         | Pause before every file edit regardless of size.                                                                                                                                                                                                                                                                                                                                                                                                          |
| `include-resolved`  | flag                                              | off                         | Also process threads Phase 2 would otherwise filter out because `isResolved` or `isOutdated` is true. Rarely useful.                                                                                                                                                                                                                                                                                                                                                                                                      |
| `deep-fix`          | `<threadId>` or `T#<threadId>`                   | off                         | Opt-in, per-thread escape hatch: route this ONE thread's fix through `/research-implement-review-report` (research → plan → plan gate → implement → review loop → report) with `--commit-mode=single`, instead of this skill's own inline fix path. No size/tag whitelist — a human naming the thread is the signal — but a hard ineligibility list still applies (see Phase 3's `deep-fix` override). Exactly one thread per invocation. When the named thread is ineligible, or `dry-run`/`no-edit`/`strict`/`no-commit` is also set, the `deep-fix` ROUTING is declined with a one-line reason and that thread falls through to its normal Phase 3/3b classification instead — neither the invocation nor the thread is aborted. Incompatible with `loop` (see Rules). See § "Dispatch model" Stage 3/3b and Phase 4. |
| `deep-fix-rounds`   | `<N>`                                             | `2`                         | Review-loop cycle count forwarded verbatim to `/research-implement-review-report`'s `--rounds`. Ignored unless `deep-fix` is also set.                                                                                                                                                                                                                                                                                                                   |

### Rules

- **One PR per invocation.** Re-invoke the skill to target a different PR.
- **Linked PRs are read-only context.** When a comment references another PR, the skill MAY read that PR's description, threads, or diff for context. It MUST NOT classify or act on comments belonging to any PR other than the target.
- **Commit eagerly after every implemented fix** — default is one commit per thread, created locally immediately, without waiting for approval first. Squash-merge release branches make extra commits free; follow-up commits after user feedback are normal (don't amend, don't rebase). Opt out with `no-commit` (explicit user request to inspect before committing); bundle under one commit with `squash`. See Phase 4.
- **Flag precedence (highest wins), stated once here — every other mention in this skill is a pointer back to this line:** an active "pause for my review" instruction (or equivalent) > `dry-run`/`no-commit` > `no-reply` > `strict`/`no-edit` > `interactive` or `autonomous` > default behavior. Next after the pause instruction, `dry-run`/`no-commit` win: nothing is committed or pushed. Next, `no-reply` wins: the skill posts no thread replies, but edits and commits can proceed. Next, `strict`/`no-edit` win: no edits without per-edit approval. Only after these does `autonomous` take effect: no gate stops. This includes the per-push go-ahead. With nothing set, the default behavior applies. Bucket A1 gates are approved. Bucket A2 gates draft and wait. Each push waits for its go-ahead. If the invocation has both `interactive` and `autonomous`, stop before Phase 1. Ask the user once which mode to use. **`deep-fix` is an action-shape selector, not a rung on this ladder** — it sits orthogonal to the chain above. Any flag that forbids editing or committing (`dry-run`, `no-edit`, `strict`, `no-commit`) DECLINES the `deep-fix` ROUTING, with a one-line reason, and the named thread falls through to its normal Phase 3/3b classification instead — the invocation is not aborted and no other thread in the cycle is affected — because `/research-implement-review-report` cannot run its research → plan → implement → review arc without editing and committing. `no-reply` still allows the run and only suppresses the reply at the end, exactly as it does for every other path today.
- **Push requires its own explicit, per-push go-ahead — commit does not.** Committing is eager and automatic (above); `git push` is not, and needs an explicit go-ahead from the user for THAT push, given in the current turn. A prior cycle's approval does NOT carry forward — re-confirm for every new push. Counts as approval: "push", "you can push", "push and reply", or an equally explicit instruction naming the push action. Does NOT count: a bare "continue"/"ok" carried over from unrelated context, or any inferred/assumed consent — ask if unsure. This gate applies only to the default path where commits are happening — `no-commit` already skips commit and push entirely and is unaffected. **Unless `autonomous` is set for this invocation. Then the push proceeds automatically once every thread in the cycle is committed (and replied to, unless `no-reply` is set). No separate go-ahead is asked for THIS invocation.** A later invocation without the flag reverts to the default gated behavior. See Phase 4.
- **`deep-fix` names exactly one thread per invocation.** `/research-implement-review-report` is a full research → plan → sign-off → implement → review-loop → report arc with a plan gate partway through (a stop with `interactive`); running it for several threads inside one cycle is not supported, and concurrent single-commit squashes on one branch would collide. Re-invoke the skill to route a different thread.
- **`deep-fix` is incompatible with `loop`.** A polling monitor cannot sit on a question or a sign-off gate for an unattended interval. If both are passed on the same invocation, STOP and ask the user which was intended rather than guessing.

## Autonomy

This workflow has three modes. The user picks one with a flag.

- Default (no flag): the run does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. The dangerous gates still stop. A dangerous gate comes before deletion of data, a post to an outside system, a push, or pull request creation. Examples of posts: GitHub comments, reviews, and issues, or documentation pages.
- `--interactive`: every gate stops and waits for the user, as the gate text says.
- `--autonomous`: no gate stops. This includes the dangerous gates. The flag is the yes of the user at each gate of this workflow, also at a gate whose text asks for an explicit yes. The run still stops for a question that blocks the work (see below).

These rules apply in all modes:

- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run passed without a stop. With `--autonomous`, also list each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It does not add steps. Some steps run only with a flag such as `--push`, `--commit-push`, or `--apply`, or only on a request of the user. Such a step still needs that flag or request.
- A flag that names an action approves that action for this run, so the action needs no new stop. Examples: `--push` and `--commit-push`. An action that a step of this workflow names as its default needs no new stop either.
- If this workflow has a merge step and the branch policy allows a merge without a review, `--autonomous` merges. Else it does not merge. Never bypass branch protection. Do not use an admin override, a force push, or a change to the branch policy. In the other modes, the merge stays with the user.
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. Delete such a branch with `git branch -D` only if both checks pass. First, its pull request is merged. Find the pull request with `list_pull_requests` (branch as `head`), then read it with `pull_request_read`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the pull request state cannot be read, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

The `autonomous` flag (default off) removes every stop of this skill: the implementation approach, the replies, `[OutOfScope]` issue creation, and the push. This skill has no merge step. A human reviewer still reviews and approves the PR before the merge, and `autonomous` does not approve the PR. Thread resolution is not a gate. After the push of a fix lands, the skill resolves the thread automatically, `autonomous` or not (see Phase 4). It applies only to the threads that this skill fixed. See the flag-precedence order in Rules for how `autonomous` ranks against `strict`/`no-edit`/`dry-run`/`no-reply`. Three buckets:

### Bucket A1: local decision gates, approved by default

Without `interactive`, the agent decides and proceeds on these gates instead of drafting and waiting. They are local: the agent changes code in the PR, and posts only the reply about the fix that it made. The invariants of Bucket B still apply. With `interactive`, each of these gates drafts and waits, as before.

- **`[ToFix]` / `[Performance]` / `[PX]` Medium/Large, only where the comment or the existing code settles the approach** — instead of "prepare the diff in chat, wait" (Phase 3 / `tag-actions.md`): implement it, and name the approach in the reply in one line.
- **`[Suggestion]` / `[Optional]` non-trivial, only where the comment or the existing code settles the direction.** Instead of drafting the trade-off and waiting, implement it. State the direction and a one-line reason in the reply. Post it as an implemented, non-draft reply (not the Draft template that Phase 3 otherwise maps non-trivial Suggestions to).
- **`[Repetition]`**: fix the pattern across all occurrences in the PR diff, instead of asking first.

### Bucket A2: gates that only `autonomous` bypasses

`autonomous` bypasses every draft-and-wait-for-confirmation checkpoint in this bucket, in any phase. With `autonomous` set, the agent decides and proceeds instead of drafting/waiting, on these gates:

- **`[ToFix]` Medium/Large where nothing settles the approach, and non-trivial `[Suggestion]` / `[Optional]` where nothing settles the direction.** That is a critical decision, so without `autonomous` the agent drafts and waits. With `autonomous`, the agent implements directly and chooses the approach itself. Note in the reply which approach it chose and why, in one line.
- **`[Question]`** — instead of "never post without an explicit human go-ahead" (`tag-actions.md`): post the answer directly, still meeting the existing draft format's quality bar (claim + reasoning + citation to file:line / test / doc). Flag in the per-cycle report (Phase 5) that a Question reply was posted autonomously — authorship risk is real, and the human should still see that it happened.
- **`[ToDiscuss]`** — instead of "never post a thread reply automatically, surface to human": post a measured reply that frames the options and tags uncertainty. Never implement a CODE change purely off a `[ToDiscuss]` thread, `autonomous` or not — the flag changes who can post the conversational reply, not what the tag authorizes.
- **Automated-review findings that trip Phase 3b's obviousness test's rewrite-from-scratch exception** — instead of falling through to draft-and-ping: the agent proceeds to implement using its own judgement anyway, applying the same "state the reasoning in the reply" discipline. This covers only that residual rewrite-magnitude case: `autonomous` is not needed for a multi-file fix, a schema-threading fix, or a `medium`/`low`-confidence fix, because Phase 3b step 5 implements all of those by default (with the question stated in the reply). Verdicts `needs-clarification` / `false-positive` / `not-applicable` still never implement anything, `autonomous` or not — there's no actionable fix available at all in those cases.
- **The per-push approval gate.** With `autonomous`, the reply and the push proceed automatically within the cycle.
- **`[OutOfScope]` issue creation.** Do not confirm the title and type with the user. Take them from the Task Composer `mode: response` draft, and run `mode: create`. In the brief, tell Task Composer that the user ran this skill with `autonomous`, which confirms `mode: create`. Pass `owner` and `repo` verbatim, as always. Name the issue fields in the cycle log (Phase 5).

### Bucket B: invariants that no flag changes

These rules are not approval gates. They are safety invariants, the contract of another tool, or a live instruction of the user. No flag changes them. Buckets A1 and A2 hold the approval gates of this skill.

- Never `git add -A` / `git add .` — explicit paths only.
- Never amend, rebase, or squash existing history; never force-push; never push to any branch other than the PR source branch.
- Never call `mcp__plugin_github_github__issue_write` directly — `[OutOfScope]` tracking always goes through Task Composer's `mode: create` flow.
- Never touch code unrelated to the reviewer's comment (PR-scope discipline).
- Never defer reviewer-stated work to a follow-up issue without the reviewer's own explicit `[OutOfScope]` tag.
- Stalemate detection stays active — stop replying automatically after 3+ exchanges show unresolved disagreement, and surface to the human.
- **A thread is only ever resolved via MCP once THIS skill itself has committed, replied to, AND pushed its fix, `autonomous` or not** — resolution never fires off the ancestry check alone, and never applies to a thread this skill did not fix (see Phase 4). `unresolve_thread` is never called unless the user explicitly asks to reopen a thread.
- **An active "pause for my review" block (or equivalent) still outranks `autonomous`** — see the flag-precedence order in Rules.

On a `deep-fix` run, pass the mode flag on. If this invocation has `interactive`, pass `--interactive` to `/research-implement-review-report`. Then its Phase 1 sign-off gate holds. If this invocation has `autonomous`, pass `--autonomous`. Then that command decides its open decisions itself and lists them in its report. Without either flag, that command approves its plan by default and still asks its open decisions.

## Workflow

### Dispatch model — two stages by default, two models

Every cycle of this workflow runs as **two** one-shot, unnamed subagent dispatches, never one — a phase that hands off to genuinely different work (mechanical extraction vs. judgment-bearing action) is its own dispatch, not folded into the other's brief, per `dev-essentials:subagent-orchestration` Rule 1 ("each logical work unit is dispatched to a subagent") and Rule 4 (delegate GitHub MCP work by default). A cycle where `deep-fix` names an eligible thread additionally runs **Stage 3** and **Stage 3b** below, described in full in Phase 4's "Stage 3 — `deep-fix` brief and outcomes" section — they are conditional, opt-in additions on top of the two-stage default, not a replacement for it.

| Stage                                            | Model                                                        | Phases                                                                        | Mandate                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Stage 1 — classifier**                         | **Haiku**                                                    | Phase 1 + Phase 2                                                             | **Read-only.** Fetch, de-noise, classify, and re-derive committed-fix state; return the Stage 1 report. No GitHub mutations, no file edits, no git writes to the working tree, index, or history — `git fetch` is expected — no verdicts, no replies.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Stage 2 — actor**                              | **Sonnet**                                                   | Phase 3 → 3b → 4 → 5 (on a `deep-fix` cycle: Phase 3 → 3b → 4 steps 1–4 only) | Consumes Stage 1's report as its only source of thread data. Every judgement call, code edit, commit, reply, and resolve happens here — except the `deep-fix` thread, which it hands off rather than acting on directly (see Phase 3's `deep-fix` override). **Carve-out for a `deep-fix` cycle:** when this cycle contains an eligible `deep-fix` thread, Stage 2's dispatch ENDS after Phase 4 step 4 (plus the single `squash`-bundle commit, if `squash` is set) — BEFORE the Push step — and hands back to the orchestrating session, which then runs Stage 3 → Stage 3b and owns this cycle's Push, Resolve, and Phase 5 itself. See Phase 4's "Dispatch hand-back for a `deep-fix` cycle" paragraph for what Stage 2 must return. |
| **Stage 3 — deep-fix** (opt-in, `deep-fix` only) | *the orchestrating session itself — not a subagent dispatch* | Phase 4 § "Stage 3 — `deep-fix` brief and outcomes"                           | Invokes `/research-implement-review-report` directly (`--commit-mode=single`) as its own next phase — per Rule 1, a phase that itself orchestrates further subagents is never folded into another dispatch's brief. Runs in the orchestrating session. That command can stop on a question, and with `interactive` on its Phase 1 sign-off gate. Questions and that gate belong to the session that talks to the user.                                                                                                                                                                                                                                                                                                     |
| **Stage 3b — deep-fix reply**                    | **Sonnet**                                                   | Phase 4 § "Stage 3 — `deep-fix` brief and outcomes"                           | One-shot GitHub dispatch (Rule 4) that posts the thread reply and resolve once Stage 3 reports its squash SHA, review-loop stop verdict, and round count.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

Stage 1's Phase 1+2 work is exactly the mechanical extraction (bracket-tag matching, thread-state filtering, git ancestry checks) the Haiku tier is scoped to, while Stage 2's Phase 3 onward is the judgement-and-execution work that stays on Sonnet, per the model matrix in the "Model selection" section of `dev-essentials:subagent-orchestration`.

**Stage 1's deliverable** is the Stage 1 report defined in [references/thread-state-schema.md](references/thread-state-schema.md) § "Stage 1 report" — one entry per active thread, carrying verbatim comment text, the precomputed T# link, the `assessedState` verdict from Phase 2 step 5, the newer-human-reply guard flag, candidate reviewer-override phrases, and a cycle-level `summary` block the orchestrating session can report from immediately without waiting for Stage 2.

**Two consequences of Stage 1 being read-only, stated once:**

- Phase 2 step 5's `cured` branch is the one place Phase 2 as written performs a GitHub mutation (the catch-up resolve). Under this split, Stage 1 only DERIVES and reports that verdict; **Stage 2 re-verifies it first, then performs the mutation as its first action, before Phase 3** — before trusting a `cured` verdict, Stage 2 runs the ancestry check (see [references/thread-state-schema.md](references/thread-state-schema.md) § "Ancestry check") itself against `origin/<headRefName>`, using the report's `claimedSha` field (no new MCP call needed); if its own check agrees with the reported verdict, it proceeds with the catch-up resolve as before — preserving step 5's "before this cycle's own Phase 3/4 run" ordering — but if it disagrees, it does NOT resolve the thread and instead falls through to the `unconfirmed-commit-claim` handling. This mirrors why Phase 4's own Resolve step always re-runs the same ancestry check (against a different `<target-ref>`) before resolving: a premature resolve misleads a human reviewer. Nothing else in step 5 changes.
- Step 5's `unconfirmed-commit-claim` branch asks the human a question. Stage 1 is a subagent and does not talk to the user, so Stage 1 reports the state in its report and the prompt is raised by Stage 2 / the orchestrating session, not by Stage 1.

**What Stage 2 may still call.** Stage 2 does NOT re-issue `pull_request_read` `method: get_review_comments` — that work is already done. It makes only the calls Stage 1 had no basis to make: `mcp__plugin_github_github__add_reply_to_pull_request_comment`, `mcp__plugin_github_github__pull_request_review_write` (`method: resolve_thread`), and any additional context a specific thread's judgement genuinely requires — most notably Phase 3b step 1–2's "read the actual code and widen the lens", which Stage 1 has no reason to have done because it assigns no verdicts. Two re-fetch exceptions:

- If a thread's file/line context in the report is STALE or CONTRADICTORY (not the legitimate `filePath: null` case used for PR-level automated-review summary banners with no file context), Stage 2 may re-fetch that single thread's current review-comment data rather than guess — the same "don't guess, ask/verify" stance `tag-actions.md`'s fall-back rules apply elsewhere.
- If `add_reply_to_pull_request_comment` reports failure for a reply Stage 2 just tried to post, `dev-essentials:github-mcp-conventions` Rule 4 requires checking whether the comment actually landed before retrying — a blind retry posts a duplicate. If the reply is already present, treat the action as handled (do not retry, do not leave it for the next cycle to rediscover); only if it is genuinely absent does Stage 2 retry the post.

**Briefing Stage 1.** `processedCommentIds` and the PR-metadata cache live in the orchestrating session, not inside a dispatch — pass both INTO each Stage 1 brief, along with every invocation parameter (`tags`, `bots`, `include-resolved`, `dry-run`, …), and require Stage 1 to return `prMetadata` back in its report. Stage 1 must STOP and report via the report's `blockers` list — never pick silently — on any of Phase 1's ask-the-user branches (`owner`/`repo` not supplied and not parseable from a URL, the target PR not found, MCP unavailable).

**Under `dry-run`:** both stages still run — Stage 2 is needed to read code, assign automated-review verdicts, and compose the drafts the dry-run report shows — but Stage 2 performs no mutation, per the existing flag semantics.

**Under `loop` (Phase 6):** each cycle re-runs the Stage 1 → Stage 2 pair fresh. The Stage 1 report is NEVER cached across cycles — thread state changes between cycles, and per-cycle re-derivation is already this skill's stance on state everywhere else (see Phase 2 step 5 and `references/thread-state-schema.md`). Only `processedCommentIds` and the PR-metadata cache carry across cycles, held by the orchestrating session.

**Phase 6 (loop/pause decision), Phase 1 step 6's one-line session header, Phase 2 step 5's `unconfirmed-commit-claim` prompt, and Stage 3 (the `deep-fix` arc) belong to neither stage's dispatch** — they run in the ORCHESTRATING SESSION itself, which already holds `interval` and the monitor-mode state across cycles, holds the plan gate of `deep-fix` (a stop with `interactive`), and which a one-shot subagent cannot print a session-lifetime header for, ask a follow-up question from, or make a cross-cycle scheduling decision on its own behalf.

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

**Fetch review comments** using `mcp__plugin_github_github__pull_request_read` with `method: get_review_comments`, which returns the PR's review threads WITH per-thread `isResolved`, `isOutdated`, and `isCollapsed` metadata (confirmed fields on this tool's schema) alongside each thread's own node ID (needed later for `resolve_thread`/`unresolve_thread` — distinct from individual comment IDs) and its comments. For PRs with many threads, paginate with `perPage` (max 100) and the cursor-based `after` param (`after` = previous page's `endCursor` from the prior response) — this method uses cursor-based pagination, a related but distinct mechanism from the page-number pagination `dev-essentials:github-mcp-conventions` Rule 3 documents. The same underlying discipline still applies: never stop after the first page, and keep paginating until a response returns no further `endCursor` (or fewer than `perPage` items).

**Pre-filter noise BEFORE classifying:**

1. Skip any comment authored by a bot not in the user-configured list. Default bot list: `["github-actions[bot]", "copilot[bot]", "coderabbitai[bot]"]`. The user may extend this list via the `bots` param. Bot comments routed through the automated-review path (Phase 3b) are an exception — they are still processed there.
2. **Filter by real thread state.** Skip any thread where `isResolved: true` OR `isOutdated: true`, unless `include-resolved` is set. This is a real status check against GitHub's own field, not a heuristic — do this BEFORE spending any classification effort on the thread, so an already-resolved or stale-diff-position thread never costs a reply. `isOutdated` means the thread's original diff position no longer exists in the current diff (later commits moved past it); its underlying comment may still be technically unresolved, but the code context it was anchored to is gone, so it is skipped by default the same as a resolved thread.
3. Build an in-memory **active roster**: `{id, threadNodeId, isResolved, isOutdated, state, commentCount, lastAuthor, lastContent, filePath, line, html_url}` per surviving thread — `threadNodeId` is required later by Phase 4's resolve call. When reading the source file in Phase 3 / Phase 3b, use `Read` with `offset: line-10, limit: 30` — reading the whole file is wasteful and also triggers per-file `.claude/rules/*.md` reminder injections, which add up.

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

   - **`cured`** (SHA resolves locally and is an ancestor of `origin/<headRefName>`) — the fix has already landed on the remote, from an earlier cycle's or invocation's push, but a prior resolve attempt is either missing or failed (this is the catch-up path — normally a resolved thread would already have been filtered out by Phase 2's `isResolved` pre-filter before reaching here). Always derive this state. If `openFindingsMarker` is `true` for this thread (see [references/thread-state-schema.md](references/thread-state-schema.md)), do NOT resolve — report `T#<id> cured (open findings) — left open.` Otherwise call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread`, `threadId: <threadNodeId>` from the roster, and `owner`/`repo`/`pullNumber` (already cached from Phase 1 — the tool's schema requires all three present on every call, even though `resolve_thread` doesn't use their values) (resolving an already-resolved thread is a documented no-op on this tool, so a stale roster entry is harmless). On success, report: `T#<id> resolved — <file>:<line>, commit <sha>.` On an MCP error, fall back to: `T#<id> cured — <file>:<line>, commit <sha> — resolve failed (<short reason>), resolve manually via GitHub UI.`
   - **`unconfirmed-commit-claim`** (SHA resolves locally but isn't yet an ancestor of the remote, OR doesn't resolve to a known commit in this checkout at all, OR the reply mentions a committed fix without a SHA that resolves cleanly) — the committed-fix reply cannot yet be confirmed safe to report as ready. Do NOT silently treat the thread as fresh or unhandled, and do NOT implement anything new on it. **There is no `autonomous` bypass for this outcome at all** — an unconfirmed SHA state needs human input regardless of `autonomous`. Report: `T#<id> already has an AI reply about a committed fix (commit <sha-or-"unspecified">) that can't be confirmed safe to report as ready — <hasn't landed on the remote yet | this checkout can't resolve the SHA locally | no SHA could be extracted from the reply>.` Leave the thread untouched until the user responds.

   See [references/thread-state-schema.md](references/thread-state-schema.md) for the reply-text matching conventions this step uses.

### Phase 3 — Act per tag

Apply the matrix in [references/tag-actions.md](references/tag-actions.md). Short summary:

Reviewer-facing tags are written as Markdown bold at the very start of the comment (e.g. `**[ToFix]**`). Match the same convention when referencing them in replies.

| Tag                                                 | Action                                                                                                                                                                                                                         |
|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `**[ToFix]**` / `**[Performance]**` / `**[PX]**`    | Small diff (< ~20 LoC, single file, no public API change) → implement, commit (eager, Phase 4), reply immediately referencing the local SHA. Push is separate, gated by approval. Larger: if the comment or existing code settles the approach, implement (§ Autonomy, Bucket A1). Else draft the diff in chat and wait. With `interactive`, always draft and wait. If `deep-fix=<threadId>` names this thread, route it through `/research-implement-review-report` instead. This applies in both modes (see the `deep-fix` override below). |
| `**[Suggestion]**` / `**[Optional]**`               | Trivial → implement like `**[ToFix]**`. Otherwise, if the comment or the existing code settles the direction, implement it and state the direction in the reply (Bucket A1). If nothing settles it, draft the trade-off in chat, then post a `**[AI][Draft]**` reply (Bucket A2). Do the same with `interactive`. Reply language respects the "optional" nature.                                                                                              |
| `**[Question]**`                                    | Draft the answer in chat, show it to the user, and post the `**[AI][Draft]**` reply ONLY after explicit user confirmation. Never post without confirmation.                                                                    |
| `**[ToDiscuss]**`                                   | Never implement. Summarize positions in chat and ask the user whether to draft a reply. Do NOT post a thread reply without that confirmation.                                                                                  |
| `**[OutOfScope]**`                                  | Never implement in this PR. If tracking requested → delegate to **Task Composer** (`dev-essentials:task-composer`): first `mode: response` to draft title/description in chat and confirm with the user (with `autonomous`, skip the confirmation, see § Autonomy, Bucket A2), then `mode: create` on approval; use ONLY the verified ID and URL it returns. Reply `**[AI]** Tracked as issue #<id>`. Never call `mcp__plugin_github_github__issue_write` directly. Without `autonomous`, this human-confirmation step always runs. |
| `**[Note]**` (and untagged)                         | Summarize in chat. No thread reply, no code edit, unless the human asks.                                                                                                                                                       |
| `**[Repetition]**`                                  | Handle as the underlying tag, and fix the pattern across all occurrences in the PR diff (Bucket A1). With `interactive`, ask first: "Apply pattern fix across all N occurrences?"                                                                                                                       |
| Automated review header                             | Run Phase 3b. `valid`/`valid-but-narrow` findings that pass the obviousness test act like `[ToFix]` and are implemented directly — size and file count are not disqualifiers, and less-than-high confidence means "ask the question in the reply AND still fix it". Only a rewrite-from-scratch-magnitude redesign, or a `needs-clarification`/`false-positive`/`not-applicable` verdict, drafts and waits. |

The "small vs. large" cut-off is **your judgement call**, not a hard rule — ~20 LoC / single file / no public API change is only a guideline (this cut-off governs `[ToFix]`/`[Performance]`/`[PX]`/trivial `[Suggestion]`; it does not govern the automated-review path — see Phase 3b step 5). Per-thread overrides from the reviewer always take precedence:

- **"Just fix it" / "no draft, apply directly"** in the thread (or in chat) → implement and commit even if you'd normally draft, provided the reviewer's intent is unambiguous.
- **"Show me a draft first" / "don't commit yet" / "let me see the diff"** → switch to draft-only for that thread even if the change is trivial. Post `**[AI][Draft]**` and wait.

When applying either override, mention it in the reply so the trail is explicit.

#### `deep-fix` override

When the invocation's `deep-fix=<threadId>` (or `T#<threadId>`) names THIS thread, and the thread is eligible (below), it does NOT take its normal per-tag action from the matrix above — it is handed to **Stage 3** (§ "Dispatch model") instead, after Phase 3b if the thread is an automated-review finding (see Phase 3b step 5's second exit). `deep-fix` names exactly one thread per invocation (see Rules); a human naming the thread is itself the eligibility signal — there is no size or tag whitelist beyond the hard ineligibility list below.

**Hard ineligibility — decline the `deep-fix` ROUTING with a one-line reason, and fall through to normal Phase 3/3b classification instead:**

| Refused                                                                 | Why                                                                                                                                                                     |
|--------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Automated-review `needs-clarification` / `false-positive` / `not-applicable` | No actionable fix exists at all — Phase 3b step 5 / `automated-review-verification.md`'s hard rules never implement anything for these verdicts.                       |
| `**[ToDiscuss]**`                                                        | Never implement a code change purely off a `[ToDiscuss]` thread (§ Autonomy, Bucket A2 — `autonomous` or not).                                                          |
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

   **Second exit from this fall-through: `deep-fix`.** When `deep-fix=<threadId>` (or `T#<threadId>`) names this thread, the exception's fall-through routes to **Stage 3** (§ "Dispatch model" and Phase 3's `deep-fix` override) instead of step 6 — a rewrite-from-scratch-magnitude finding is precisely the case `/research-implement-review-report` exists to work: research the precedent, surface the design choice for sign-off, implement, review. `needs-clarification` / `false-positive` / `not-applicable` verdicts remain ineligible for `deep-fix` regardless of this exit — see Phase 3's ineligibility table.

   **Confidence is not a gate — it changes what you SAY, not what you DO.** With `confidence: high`, implement and reply as below. With `medium` or `low` — or whenever you are uncertain about the RIGHT approach rather than about whether to fix at all — **still implement your best-judgment fix**, and additionally state the uncertainty as an explicit question in the chat report and in the thread reply: `Implemented <X>. Open question: <the specific choice you made and the alternative>. Say the word and I'll switch.` Asking and fixing are not alternatives — **ask AND fix**. The only thing that stops the fix is the rewrite-from-scratch exception above. (Do not confuse this with the `needs-clarification` verdict, which is about whether there is a defect at all — that verdict is still never implemented.)

   Conditions hold → treat exactly like `[ToFix]`: implement, commit (Phase 4), and post a non-draft `**[AI]**` "Implemented fix" reply (see the reply templates below) — skip the draft/ping-approval steps entirely for this thread; there is no draft stage on this path. The exception applies → continue to step 6.
6. Post `**[AI][Draft]**` reply using one of the verdict templates in `references/automated-review-verification.md`. Every template ends with `*Draft pending author confirmation.*` — include this closing line.
7. Ping the human in chat. Do NOT edit code. Wait for approval before implementing.

### Phase 4 — Commit, reply, push, then flag for resolution

Reply happens right after commit, before push, so the reply text never overclaims: it reports what is locally committed, not what a reviewer can already see. Resolving a thread is a different kind of claim — it tells a human reviewer the fix is visible to them, which isn't true until the push has actually landed. `mcp__plugin_github_github__pull_request_review_write`'s `resolve_thread` method (confirmed on this MCP server's tool surface: takes `threadId`, plus `owner`/`repo`/`pullNumber` — the tool's JSON schema requires all three present on every call, even though `resolve_thread` doesn't use their values, so pass the same `owner`/`repo`/`pullNumber` already cached from Phase 1; resolving an already-resolved thread is a documented no-op) is what makes that claim true, so this skill calls it itself, but ONLY after the push that makes it true has actually landed — never before. Push itself is gated by an explicit, per-push user approval (see Rules; unless `autonomous` is set) and happens once per cycle, after every thread below has been verified, committed, and replied to.

For every thread being fixed this cycle, do the following in order before moving to the next thread:

**Exception when `squash` is set:** steps 1–2 (verify, stage) still run per thread inside this loop, but step 3's single commit does not exist until the end of the cycle (see the `squash` bullet under step 3) — so step 4's reply cannot reference a per-thread SHA yet. Run steps 1–2 for every thread first, create the single end-of-cycle commit, THEN loop back and run step 4 for every thread, each reply referencing that one shared SHA, before moving on to push.

**Exception when `deep-fix=<threadId>` names a thread eligible per Phase 3's `deep-fix` override:** that thread does NOT run steps 1–4 in this per-thread loop. It is dispatched separately, as **Stage 3** (§ "Dispatch model"), which runs LAST in the cycle — after every other thread's steps 1–4 above (including a `squash`-bundle commit, if `squash` is also set) and BEFORE the cycle's single push below. This ordering guarantees nothing else commits on the branch between the `HEAD` Stage 3 records and the single commit it produces. See the "#### Stage 3 — `deep-fix` brief and outcomes" section for the full brief contract, reply/resolve rules, and the `stop-blocked` path.

**Dispatch hand-back for a `deep-fix` cycle.** Because Stage 3 runs in the orchestrating session, not in a dispatch (§ "Dispatch model"), **Stage 2's own dispatch ENDS HERE** on such a cycle — after steps 1–4 have run for every other thread, plus the single `squash`-bundle commit if `squash` is set, and BEFORE the Push step below. Stage 2 returns to the orchestrating session: the `deep-fix` thread's `threadId` (at minimum), plus its `filePath`/line range, verbatim reviewer text, tags or automated-review verdict + confidence, the SHAs it committed this cycle (or the one `squash` SHA), and which threads it already replied to. The orchestrating session then runs Stage 3, dispatches Stage 3b, and owns this cycle's Push, Resolve, and Phase 5 itself — Stage 2 performs none of those on a `deep-fix` cycle. On a cycle with no eligible `deep-fix` thread nothing changes: Stage 2 runs Phase 4 through Resolve and Phase 5 as before.

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

**Push — once per cycle, after steps 1–4 above have run for every thread in the cycle:** gated by an explicit, current-turn user go-ahead (see Rules; a prior cycle's approval does not carry forward) — unless `autonomous` is set, in which case proceed directly to push once all threads in the cycle are committed (and replied to, unless `no-reply` is set). `git push` once for the whole cycle's commits — this holds whether they were one-per-thread or bundled via `squash`; either way, exactly one push per cycle. Never force-push. Never push to a protected branch other than the current PR source branch. If approval hasn't arrived by the time the cycle log is printed, leave the commits unpushed and say so explicitly in Phase 5 (`N commits ready, not yet pushed — push when ready`) — the replies already posted stay accurate, since they only ever claimed a commit, never a push; no thread from this cycle is resolved until the push actually lands (see "Resolve threads and report" below). **Exception:** if this cycle ran a `deep-fix` thread and it ended `stop-blocked`, this cycle's push is cancelled entirely — not just for that thread — see "Stage 3 — `deep-fix` brief and outcomes" below.

**Resolve threads and report — runs after this cycle's push succeeds, for (a) the threads this cycle just committed and replied to, AND (b) any thread Phase 2 step 5 flagged this cycle as `unconfirmed-commit-claim`:** once `git push` succeeds:

- For each thread committed and replied to in steps 1–4 above this cycle (and NOT carrying `openFindingsMarker: true` — see the Deep-fix outcomes below), run the ancestry check (see [references/thread-state-schema.md](references/thread-state-schema.md) § "Ancestry check") for that commit's SHA against `<pushed-tip>` — the just-pushed commit/branch state this cycle's own push produced, not the remote-tracking ref. Success (expected, since the push just carried that commit) → call `mcp__plugin_github_github__pull_request_review_write` with `method: resolve_thread`, `threadId: <threadNodeId>` from the Phase 2 roster, and `owner`/`repo`/`pullNumber` (cached from Phase 1 — required by the tool's schema even though `resolve_thread` ignores their values). On success, report the thread resolved: `T#<id> resolved — <file>:<line>, commit <sha> pushed as part of this cycle.` On an MCP error, report instead: `T#<id> pushed but resolve failed (<short reason>) — resolve manually via GitHub UI.` Failure of the ancestry check itself → the commit isn't actually on the pushed branch (e.g. dropped, rebased away) → do NOT call resolve; report the thread as still open; do not guess. A thread with `openFindingsMarker: true` is never resolved here — see "Stage 3 — `deep-fix` brief and outcomes" below.
- For each thread Phase 2 step 5 flagged this cycle as `unconfirmed-commit-claim`, re-run the same ancestry check against `<pushed-tip>` when a SHA exists to check; for the sub-case where no SHA cleanly resolved at all, there is nothing to re-check and resolution can only ever come from the human's own direction. The resolve is conditional on the human's answer to Phase 2 step 5's prompt (tracked as conversational context within this same session / `/loop` run, not a persisted file — the answer only needs to survive until this cycle's Phase 4, not across sessions), not on ancestry alone: only if the human explicitly answered that prompt this session with a push-and-resolve direction for this specific thread, AND (where a SHA exists) the ancestry check against `<pushed-tip>` now succeeds → resolve and report the same way, rather than waiting for a later cycle to catch it via Phase 2 step 5. If the human never answered, or answered "handle separately" (or equivalent), leave the thread open regardless of what this cycle's push did — do not resolve on push alone. If the ancestry check still fails (the flagged commit wasn't part of this cycle's push), leave it open as well — a later cycle's Phase 2 step 5 will keep re-checking it.

Threads carried over from an EARLIER cycle or invocation — where a fix was committed and replied to, but that cycle ended before its push happened — are NOT tracked here via any persisted state. Instead, Phase 2 step 5 re-derives that state directly at the top of every cycle: it re-reads each active thread's existing `**[AI]** Fixed: ... Committed as <sha>` reply (already part of the thread's comment history fetched in Phase 2) and runs the ancestry check against `origin/<headRefName>`. If that check now succeeds (an earlier cycle's later push already landed it), Phase 2 resolves the thread as a catch-up step. If it doesn't yet succeed, Phase 2 surfaces it to the user instead of silently reprocessing it — there is no `autonomous` bypass for this outcome. Note that in normal operation this catch-up path fires rarely: once a resolve call succeeds, the thread's `isResolved` flips true on GitHub itself, and Phase 2's pre-filter (see Phase 2 step 2) skips it on every later fetch before step 5 ever runs — the catch-up path exists mainly for a failed resolve call or a reply posted before this skill supported resolving. This re-derivation is simpler and inherently correct across sessions/invocations — it depends on GitHub's own thread history and real git ancestry, not on any file surviving between runs.

If push approval doesn't arrive this cycle (or the push fails), no thread from this cycle is resolved — leave them open, with the reply already posted; a later cycle's Phase 2 step 5 (or a retry of this same push) will find the reply and resolve it once the push actually lands (Phase 5's cycle log already carries the unpushed state as `N commits ready, not yet pushed — push when ready`).

Splitting commits when one file covers multiple threads:

- For files touched by more than one thread, reset the file to `HEAD` after capturing the final state, then re-apply each thread's edit and commit it before moving to the next.

Bundle threads that share one pattern:

- When three-plus threads carry the **same reviewer note** applied at different call sites, treat them as one logical fix with one commit and reply on each thread pointing at the shared SHA.

#### Stage 3 — `deep-fix` brief and outcomes

**Pre-flight — establish the checkout root before dispatching anything.** Resolve the local checkout root with `git rev-parse --show-toplevel` and use that ABSOLUTE path as the worktree path in the brief below; then confirm `git rev-parse --abbrev-ref HEAD` in that root equals the PR's `headRefName` (Phase 2 step 5 deliberately does not assume it does). If either check fails or disagrees, STOP and ask the user before checking out, switching, or creating anything.

**Invocation.** Stage 3 runs `/research-implement-review-report` as the orchestrating session's own next phase — never folded into Stage 2's brief (Rule 1: a phase that itself orchestrates further subagents is its own dispatch), and never delegated to a subagent. That command can stop on a question, and with `interactive` on its Phase 1 sign-off gate. Questions and that gate belong to the session that talks to the user. Pass:

1. The **branch name** (the PR's `headRefName`) and the **absolute worktree path** — the two facts that command's own pre-existing-branch verification step needs.
2. `--base=<baseRefName>` — the PR's own target branch, already cached from Phase 1.
3. `--commit-mode=single` and `--rounds=<deep-fix-rounds>`.
4. **Commit-subject override** — the single squash commit MUST use this skill's own Phase 4 step 3 format: `PR #<prId> T#<threadId>: <subject>`, body explaining *why* and referencing the reviewer's point, the `Co-Authored-By` trailer.
5. **Squash-window exclusivity** — no other commit will land on this branch between the recorded `HEAD` and the squash (see the ordering rule above). If that command's own squash-base safety stop trips anyway, let it stop and report — do not override it.
6. **Scope guard** — the fix stays inside files/areas already touched by this PR's diff and addresses only this thread.
7. **Artifact guard** — never stage or commit that command's own research/plan/report artifacts, and never reference their paths in the thread reply or the commit message — pipeline-internal artifacts stay out of anything shipped (`dev-essentials:engineering-discipline` Rule 3).
8. **No push, ever** — this skill owns the single per-cycle push, and `/research-implement-review-report` already never pushes without the user's own explicit go-ahead.
9. Expect back: the squash SHA, the review-loop stop verdict (`stop-clean` / `stop-max-rounds` / `stop-blocked`), the round count, and the deferred-findings list.
10. `--interactive` or `--autonomous`, for an invocation that has `interactive` or `autonomous`.

**Reply and resolve, by `/research-implement-review-report`'s stop verdict** — Stage 3b (a one-shot Sonnet GitHub dispatch, Rule 4) posts the reply and the resolve once Stage 3 reports its squash SHA, stop verdict, and round count:

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

**`stop-blocked` — cancel the cycle's push.** `/research-implement-review-report`'s `--commit-mode=single` will already have made review-loop's per-round commits on the PR's source branch before it can know the build is red — step 1's "do NOT commit if the build fails" rule cannot prevent commits that already happened inside that command's own arc. So: do NOT squash, do NOT post a `**[AI]**` "Fixed" reply, and do NOT post `**[AI][Draft]**` either — `automated-review-verification.md` reserves that prefix for a proposal, and a half-finished commit stack is not a proposal. **Cancel this cycle's push entirely** (every thread's commits, not just this one) and STOP: report to the user that red commits already sit on the PR source branch and pushing would publish a broken PR. Report it in Phase 5 as `deep-fix — blocked (build red, not pushed)`, and offer the two real recovery options: fix forward in this session, or reset the branch back to the pre-Stage-3 SHA (a new commit / `git reset` on this **unpushed** tip only — Bucket B still forbids amending or rewriting *pushed* history).

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

**Thread resolution after a fix lands — the `no-reply` split.**

- **`no-reply` NOT set (default):** reply then resolve, per Phase 4's Reply / Push / Resolve mechanics above.
- **`no-reply` set:** do NOT post the `**[AI]** Fixed` reply, and do NOT resolve the thread automatically — the reply is the audit trail of why the thread is resolved, so without it the auto-resolve step is suppressed. Instead, report the cured thread to the user in chat with the file path, line range, and commit SHA (e.g. `T#<id> cured — <file>:<line>, commit <sha> — resolve manually via the GitHub UI when ready`). The user resolves the thread manually after reviewing the committed diff. This applies to a Phase 4 fresh fix exactly as it applies to a Phase 2 step 5 catch-up.

**Thread resolution is scoped to threads this skill itself fixed.** `mcp__plugin_github_github__pull_request_review_write` (`method: resolve_thread`, taking the thread's node ID) is a real, confirmed tool on this MCP server's surface, and the skill calls it — but ONLY once the eligibility rule above is met (committed, replied to, AND actually pushed), never speculatively and never for a thread it did not itself fix:

- **Resolve** — threads meeting the eligibility rule above where the change demonstrably addresses the reviewer's point (e.g., `[ToFix]`, `[Performance]`, automated-review-derived fixes where coverage was implemented).
- **Never resolve** — false-positive analysis threads (the reviewer reads and resolves at their own pace), `[Note]` / acknowledgement-only threads, automated-review summary banners (never touched at all), out-of-scope items (leave open after the tracking-issue reply), a thread whose fix came from a `deep-fix` run that ended `stop-max-rounds` with outstanding findings (`openFindingsMarker: true` — see "Stage 3 — `deep-fix` brief and outcomes" above), and any thread that doesn't yet meet the eligibility rule above. `unresolve_thread` is never called at all unless the user explicitly asks to reopen a specific thread.

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

`T#12`'s reply is already live, but it is NOT resolved this cycle — that waits for its commit to actually be pushed (see Phase 4). `T#9` illustrates the carried-over-thread mechanic: its fix was committed and replied to back in cycle 1, but cycle 1 ended (one-shot default, Phase 6 rule 1) before that commit got pushed. At the start of cycle 2, Phase 2 step 5 re-read `T#9`'s existing `**[AI]** Fixed: ... Committed as 9f3a1c2` reply, found it was not yet an ancestor of `origin/<headRefName>`, and flagged it `unconfirmed-commit-claim`, surfacing the prompt to the human — who answered this session with a push-and-resolve direction for `T#9`. Cycle 2's push happened to include commit `9f3a1c2`, so once that push landed, cycle 2's own "Resolve threads and report" step re-ran the ancestry check against `<pushed-tip>` and — the human having authorized it — called `resolve_thread` for `T#9`, and reported it resolved — same cycle as the push, not a later close-out notice. Because the resolve call flips `T#9`'s `isResolved` to `true` on GitHub itself, cycle 3's Phase 2 pre-filter would skip it before it ever reaches the roster — it will not appear in cycle 3's table at all.

With `squash`, replace the per-thread commit SHAs with a single end-of-cycle line: `Cycle commit a1b2c3d (T#12, T#14, T#18).` With `no-commit`, replace the SHA segment with `staged locally`.

Always end the log with an explicit push-status line so it is never ambiguous whether the reviewer can see the fix yet: `N commits ready, not yet pushed — push when ready` when this cycle's commits are still awaiting the user's push approval, or `N commits pushed as <sha(s)>` once approval arrived (or `autonomous` applied) and the push landed.

A `deep-fix` thread's row uses one of `deep-fix (N rounds, clean)`, `deep-fix — open findings`, or `deep-fix — blocked` in place of the usual `<short outcome>` — see [references/thread-state-schema.md](references/thread-state-schema.md) § "Cycle log" for the full outcome-value list. A cycle whose `deep-fix` run ended `stop-blocked` prints `deep-fix — blocked (build red, not pushed)` in place of the usual push-status line, since that cycle's push was cancelled entirely (see Phase 4's "Stage 3" outcomes). **On a `deep-fix` cycle this whole cycle log is printed by the ORCHESTRATING SESSION, not by Stage 2** — Stage 2's dispatch already ended after Phase 4 step 4 (see § "Dispatch model", Stage 2's carve-out), so the orchestrating session composes these rows from Stage 2's returned per-thread results plus Stage 3's own reported squash SHA, stop verdict, and round count.

Add a comment ID to `processedCommentIds` only AFTER its action (or explicit skip decision) completes successfully. On failure, leave it unprocessed so the next cycle retries.

### Phase 6 — Loop and pause

Default is **one-shot**; monitoring is opt-in.

1. **No `loop` flag and no outer `/loop` wrapper (default)** → exit after the first cycle. Announce: `Monitoring skipped (one-shot default). Pass 'loop' to start polling.`
2. **Already wrapped in `/loop`** → return control to `/loop`; it performs the sleep and re-invokes. Do NOT start a nested `/loop`.
3. **`loop` flag set on a standalone invocation** → at end of first cycle, auto-enter monitoring:

   ```text
   /loop <interval> /process-pr-comments pr=<id> owner=<owner> repo=<repo> [other original params except 'loop', 'deep-fix', and 'deep-fix-rounds']
   ```

   Forward every param the user supplied except `loop` (the inner invocation no longer needs it — it runs under `/loop`) and `deep-fix`/`deep-fix-rounds` (already incompatible with `loop` — see Rules — a polling monitor cannot sit on a question or a plan gate unattended, so it is dropped from the re-invocation rather than re-triggered). `interactive` and `autonomous` are forwarded, so every monitor tick runs in the same mode. The `interval` is the resolved value (default `15m`). Announce the transition: `Entering monitor mode: /loop <interval>.`

If the PR transitions to `closed` or `merged` during any cycle, stop the loop and tell the user.

## Stalemate detection

Count only the `**[AI]**`-prefixed replies (including the legacy plain `[AI]` form) paired with the reviewer's responses that followed them — i.e., back-and-forth exchanges between Claude and the reviewer(s) across the thread's full history, not just the current session. The author's own non-AI replies are NOT counted (the author may legitimately add context without it being a stalemate).

If that exchange count exceeds 3 AND the latest two exchanged replies show unresolved disagreement, stop replying automatically. Surface the thread to the human in chat with the suggestion: "Consider escalation, a design review, or talking this out synchronously."

## Safeguards

- Do NOT touch code unrelated to the reviewer's comment (respect PR scope).
- Do NOT post replies when `dry-run` or `no-reply` is set.
- Do NOT implement edits when `dry-run`, `no-edit`, or `strict` is set; draft only.
- Do NOT commit or push when `dry-run` or `no-commit` is set.
- **Do NOT push without an explicit, current-turn user go-ahead** (see Rules and Phase 4's "Push" paragraph). Commit is eager and automatic; push is not, and a prior cycle's approval does not carry forward. The sole exception is `autonomous` — see the flag-precedence order in Rules for how these rank against an active "pause for my review" instruction, `dry-run`, and `no-commit`.
- **Do NOT resolve a thread before its commit has actually been pushed.** Reply happens early (right after commit, before push); the resolve call happens late — only once that commit's push actually lands, whichever cycle or invocation that happens in — see Phase 4.
- Do NOT amend, rebase, squash existing history, or force-push. Always create fresh commits.
- Do NOT push to any branch other than the PR source branch. Never push to `master`, `release/*` target branches, or any protected ref.
- Do NOT invent issue fields for Task Composer. Confirm the title and type with the user first. With `autonomous`, take them from the Task Composer draft instead, and name them in the cycle log (§ Autonomy, Bucket A2).
- Do NOT reprocess a comment already in `processedCommentIds` within the same session.
- **Never defer reviewer-stated work to a follow-up issue.** When a reviewer or the author has stated WHAT should happen on a thread — explicitly, even in their own follow-up reply — act on that statement in the **current PR**. Forbidden reply phrasings (without explicit prior user direction to defer): "Tracked as a separate follow-up issue.", "Will be addressed in a follow-up PR.", "A migration will be tracked as a follow-up.", "Out of scope for this round.", or any equivalent "we'll do this later" framing. The `[OutOfScope]` reviewer tag is the ONLY tag that cleanly authorizes deferral, and only when the reviewer explicitly used it. An automated-review or `[ToFix]` finding paired with a clarifying author reply is a directive, not optional. If you genuinely believe the work should be deferred, STOP and ask the user before posting any reply or commit. Never invent a deferral.
- Do NOT call any GitHub MCP tool with inferred `owner` or `repo` — always pass user-supplied or URL-parsed values verbatim (see `dev-essentials:github-mcp-conventions` Rules 1–2).
- **Do NOT resolve or unresolve any thread this skill did not itself fix, commit, reply to, AND push in this session** — the `resolve_thread` call in Phase 4 is scoped strictly to those threads. Never call `unresolve_thread` unless the user explicitly asks to reopen a specific thread. No flag, including `autonomous`, changes this.
- **Never stage or commit a `deep-fix` run's research/plan/report artifacts, and never reference their paths in a thread reply or commit message** — pipeline-internal artifacts stay out of anything shipped (`dev-essentials:engineering-discipline` Rule 3; see Phase 4's "Stage 3" brief).
- **Never push a cycle whose `deep-fix` run ended `stop-blocked`.** Cancel that cycle's push entirely — every thread's commits, not just the `deep-fix` thread's — and STOP; see Phase 4's "Stage 3" outcomes.

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

# Full autonomy: implement, decide, reply, create issues, push, with no pauses (a human still reviews and approves the PR before merge)
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo autonomous

# Route one Medium/Large [ToFix] thread through research-implement-review-report instead of drafting it
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo deep-fix=T#2201458823

# Same, with a 3-round review loop instead of the default 2
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo deep-fix=2201458823 deep-fix-rounds=3

# Old default: draft and wait for larger fixes
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo interactive

# Already wrapped in /loop — outer harness controls cadence
/loop 15m /process-pr-comments pr=42 owner=Vasar007 repo=my-repo
```
