---
name: process-pr-comments
description: "Process the review comments of a GitHub pull request as its author. It fixes what the comment or the code settles, commits each fix, and drafts the replies that need a human decision. A comment that the reviewer marks as out of scope gets a GitHub issue. Without 'autonomous', each new issue and each push wait for the go-ahead of the user."
when_to_use: "Use it for 'process PR comments' or 'address review comments'. Use it also for a PR URL with a request to act on it."
---

# Process PR Review Comments

## Purpose

The skill acts as the PR author. In each cycle, it skips the threads that GitHub marks as resolved or outdated, and classifies each remaining comment by its review tag. Then it fixes, drafts, answers, or opens a tracking issue, and posts a short reply. Each reply starts with the bold marker `**[AI]**`, so that reviewers can tell the replies of Claude from the replies of the author. Reviewers bold their leading tags in the same way, for example `**[ToFix]**`.

Each fix gets a local commit at once. Its `**[AI]** Fixed` reply names the local commit SHA, before any push. The push is a separate step that comes once per cycle, after every reply. It needs the go-ahead of the user, unless `autonomous` is set (see Rules). After the push lands, the skill resolves each thread that it fixed with `pull_request_review_write` (`method: resolve_thread`).

Each cycle runs as two subagent dispatches. Stage 1 fetches and classifies, and changes nothing. Stage 2 acts. Only the orchestrating session talks to the user. Stage 2 returns its open questions. The orchestrating session asks the user, and then resumes the same Stage 2 agent with `SendMessage` (see "Dispatch model").

## When NOT to use

- Review of code that someone else wrote. That is the reviewer side, and other workflows handle it.
- Creation of a PR, a change to its description, or a change of reviewers. These are out of scope for this skill. To write the PR description text, use `dev-essentials:pr-composer` (or `/compose-pr`).
- Resolve or unresolve of a thread that this skill did not fix (see Bucket B).

## Prerequisites

1. The GitHub MCP tools (`mcp__plugin_github_github__*`) must be available. If they are missing, stop. Ask the user to reconnect them with `/mcp`, then try again (see `dev-essentials:github-mcp-conventions` Rule 5).
2. The user must give the explicit **`owner`** and **`repo`** values, or a full GitHub PR URL that holds them. Never infer them from the git remote or from the session context (see `dev-essentials:github-mcp-conventions` Rule 1).
3. To create an issue for an `[OutOfScope]` comment, the Task Composer agent (`task-composer` from `dev-essentials`) must be loaded.
4. `deep-fix` also needs the command `/research-implement-review-report` of this plugin. If the command is not available, decline the `deep-fix` routing with a one-line reason. The thread then gets its normal Phase 3 or Phase 3b classification (see Rules).

## Rules

- **One PR per invocation**. To work on another PR, invoke the skill again.
- **Linked PRs are read-only context**. A comment can point to another PR. The skill can then read the description, the threads, or the diff of that PR for context. It MUST NOT classify or act on the comments of any PR other than the target.
- **Commit at once after each implemented fix**. The default is one local commit for each thread, made at once, with no approval first. Follow-up commits after feedback of the user are normal. Do not amend, and do not rebase. `no-commit` turns the commits off, for a user who wants to inspect first. `squash` puts the fixes of the cycle into one commit. See Phase 4.
- **Flag precedence, highest first**. This list is the only statement of the order. Every other mention in this skill points here.
  1. An active "pause for my review" instruction, or an equivalent one.
  2. `dry-run` or `no-commit`: nothing is committed or pushed.
  3. `no-reply`: the skill posts no thread replies. Edits and commits can go on.
  4. `strict` or `no-edit`: no edit without an approval for that edit.
  5. `interactive` or `autonomous`. If no flag above blocks an action, `autonomous` stops no gate. This includes the go-ahead for each push.
  6. The default behavior. Bucket A1 gates are approved. Bucket A2 gates draft and wait. Each push waits for its go-ahead.

  If the invocation has both `interactive` and `autonomous`, stop before Phase 1. Ask the user once which mode to use.

  **`deep-fix` is not a level of this order**. It selects the form of the action for one thread. `/research-implement-review-report` must edit and commit to run its arc. So each flag that forbids edits or commits DECLINES the `deep-fix` routing, with a one-line reason. These flags are `dry-run`, `no-edit`, `strict`, and `no-commit`. The named thread then gets its normal Phase 3 or Phase 3b classification. The invocation does not stop, and no other thread of the cycle changes. `no-reply` still allows the run, and only suppresses the reply at the end, as on every other path.
- **Each push needs its own explicit go-ahead. A commit does not**. Commits are automatic (see above). `git push` needs an explicit go-ahead of the user for THAT push, in the current turn. The approval of an earlier cycle does NOT carry over, so ask again for each new push. These count as approval: "push", "you can push", "push and reply", or an equally explicit instruction that names the push. These do NOT count: a bare "continue" or "ok" from an unrelated context, and any inferred or assumed consent. If you are not sure, ask. The gate applies only to a run that makes commits. `no-commit` already skips the commit and the push. **With `autonomous`, the push goes ahead without a question after every thread of the cycle is committed and replied to (with `no-reply`: committed)**. For this invocation, the skill asks for no go-ahead. A later invocation without the flag goes back to the gated default. See Phase 4.
- **`deep-fix` names exactly one thread per invocation**. `/research-implement-review-report` is a full arc with a plan gate partway through (a stop with `interactive`). The skill cannot run it for several threads in one cycle, and parallel single-commit squashes on one branch collide. To route another thread, invoke the skill again.
- **`deep-fix` is not allowed together with `loop`**. A polling monitor cannot wait at a question or a sign-off gate for an unattended interval. If an invocation has both, STOP and ask the user which one they meant. Do not guess.

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
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If both checks below pass, you can delete such a branch with `git branch -D`. First, its pull request is merged. Find the pull request with `list_pull_requests`, with `head: "<owner>:<branch>"` and `state: "all"`. `<owner>` is the `owner` value of the call. The default state lists open pull requests only, and GitHub ignores a `head` value without the `<owner>:` prefix. Then read the pull request with `pull_request_read` (`method: "get"`), and make sure that `merged` is `true`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the run cannot read the state of the pull request, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

The `autonomous` flag (default off) removes every stop of this skill: the approach of the implementation, the replies, the `[OutOfScope]` issue creation, and the push. This skill has no merge step. A human reviewer still reviews and approves the PR before the merge, and `autonomous` does not approve the PR. Thread resolution is not a gate. After the push of a fix lands, the skill resolves the thread on its own, with or without `autonomous` (see Phase 4). For the rank of `autonomous` against the other flags, see the flag precedence in Rules. The gates fall into three buckets.

### Bucket A1: local decision gates, approved by default

Without `interactive`, the agent decides and goes on at these gates. It does not draft and wait. The gates are local: the agent changes code in the PR, and posts only the reply about its own fix. The invariants of Bucket B still apply. With `interactive`, each of these gates drafts and waits.

- **`[ToFix]`, `[Performance]`, or `[PX]`, Medium or Large, where the comment or the existing code settles the approach**. Implement it, and name the approach in one line of the reply. This replaces "prepare the diff in chat, wait" of `tag-actions.md`.
- **`[Suggestion]` or `[Optional]`, non-trivial, where the comment or the existing code settles the direction**. Implement it. State the direction and a one-line reason in the reply. Post it as an implemented reply, not as the Draft template that `tag-actions.md` uses for the other non-trivial suggestions.
- **`[Repetition]`**: fix the pattern at all its places in the PR diff. Do not ask first.

### Bucket A2: gates that only `autonomous` bypasses

Without `autonomous`, each gate in this bucket drafts and waits for the approval of the user, in every phase. With `autonomous`, the agent decides and goes on at these gates:

- **`[ToFix]` Medium or Large where nothing settles the approach, and `[Suggestion]` or `[Optional]` non-trivial where nothing settles the direction**. That choice is a critical decision, so the default drafts and waits. With `autonomous`, implement it directly, and choose the approach yourself. Name the approach and the reason in one line of the reply.
- **`[Question]`**: post the answer directly. Without `autonomous`, `tag-actions.md` forbids a post without an explicit go-ahead of a human. The answer keeps the quality of the draft format: a claim, the reasoning, and a citation (file and line, test, or doc). A wrong public answer under the identity of the author misleads reviewers. So the cycle report (Phase 5) states each Question reply that the skill posted without a stop.
- **`[ToDiscuss]`**: post a measured reply that frames the options and marks the uncertainty. Without `autonomous`, the skill posts no reply and surfaces the thread to the human. Never implement a CODE change only because of a `[ToDiscuss]` thread, with or without `autonomous`. The flag changes who can post the reply, not what the tag allows.
- **Automated-review findings at the rewrite-from-scratch exception or at the third condition (new architecture or new public contract) of the obviousness test (Phase 3b step 5)**: implement with your own judgment, and state the reasoning in the reply. Add each such fix to the list "Decisions for your review" of the cycle log (Phase 5). Without `autonomous`, such a finding drafts and waits. Every fix that `autonomous` implements on this path must still meet the second condition (Bucket B). A fix that leaves the files and areas of the PR diff drafts and waits, also with `autonomous`. Some fixes do not need `autonomous`: a fix across several files, a fix that threads a field through a schema, and a fix with `medium` or `low` confidence. Phase 3b step 5 implements all of them by default, with the question in the reply. The verdicts `needs-clarification`, `false-positive`, and `not-applicable` never implement anything, with or without `autonomous`. They have no fix to make.
- **The approval gate for each push**. With `autonomous`, the reply and the push go ahead in the cycle without a stop.
- **`[OutOfScope]` issue creation**. Do not ask the user to approve the title and the type. Take the title from the `mode: response` draft of Task Composer. If the reviewer or the user named a type, pass it. Else pass no type, and Task Composer leaves `type` out. Then run `mode: create`. In the brief, tell Task Composer that the user ran this skill with `autonomous`, which approves `mode: create`. Pass `owner` and `repo` word for word, as always. Name the issue fields in the cycle log (Phase 5).

### Bucket B: invariants that no flag changes

These rules are not approval gates. They are safety invariants, the contract of another tool, or a live instruction of the user. No flag changes them. Buckets A1 and A2 hold the approval gates of this skill.

- Never `git add -A` or `git add .`. Stage explicit paths only.
- Never amend, rebase, or squash pushed history or a commit that this run did not make. Always make new commits. Never force-push. One exception: `deep-fix` can squash or reset the unpushed commits of its own arc (`references/deep-fix.md`).
- Never push to a branch other than the PR source branch. Never push to `master`, to a `release/*` target branch, or to any protected ref.
- Never call `mcp__plugin_github_github__issue_write` directly. `[OutOfScope]` tracking always goes through the `mode: create` flow of Task Composer. Never invent issue fields.
- Never touch code that the comment of the reviewer does not cover (PR-scope discipline).
- Never call a GitHub MCP tool with an inferred `owner` or `repo`. Pass the values of the user or of the URL word for word (see `dev-essentials:github-mcp-conventions` Rules 1 and 2).
- Never reprocess a comment that is already in `processedCommentIds` in the same session.
- **Never defer work that a reviewer stated to a follow-up issue**. A reviewer or the author can state WHAT to do on a thread, also in their own follow-up reply. Act on that statement in the **current PR**. Without an explicit earlier direction of the user to defer, never use a "we do this later" phrasing. Examples: `Tracked as a separate follow-up issue.`, `Will be addressed in a follow-up PR.`, `A migration will be tracked as a follow-up.`, `Out of scope for this round.`, and the like. The `[OutOfScope]` tag of the reviewer is the ONLY tag that allows a deferral, and only after the reviewer used it explicitly. An automated-review or `[ToFix]` finding with a clarifying reply of the author is a directive, not an option. If you believe that the work needs a deferral, STOP and ask the user before you post any reply or make any commit. Never invent a deferral.
- Stalemate detection stays on (see "Stalemate detection").
- **The skill resolves a thread through MCP only after it committed, replied to, AND pushed its own fix, with or without `autonomous`**. An ancestry check alone never resolves a thread, and the skill never resolves a thread that it did not fix (see Phase 4). It never calls `unresolve_thread`, unless the user explicitly asks to reopen a specific thread.
- **An active "pause for my review" instruction, or an equivalent one, still outranks `autonomous`**. See the flag precedence in Rules.
- **Never stage or commit the research, plan, or report artifacts of a `deep-fix` run. Never put their paths in a thread reply or a commit message**. Pipeline-internal artifacts stay out of anything that ships (`dev-essentials:engineering-discipline` Rule 3).
- **Never push a cycle whose `deep-fix` run ended `stop-blocked`**. Cancel the push of that whole cycle, for the commits of every thread, and STOP (see `references/deep-fix.md`).

On a `deep-fix` run, pass the mode flag on. With `interactive`, pass `--interactive` to `/research-implement-review-report`. Then its Phase 1 sign-off gate holds. With `autonomous`, pass `--autonomous`. Then that command decides its open decisions itself and lists them in its report. Without either flag, that command approves its plan by default and still asks about its open decisions.

## Parameters

Pass the parameters as free-form `key=value` pairs and standalone flags in the skill arguments. `pr` is required. `owner` and `repo` are required for a PR number. All other parameters are optional.

| Param | Values | Default | Meaning |
| --- | --- | --- | --- |
| `pr` | `<id>` or full GitHub PR URL | Required | The target PR. A full URL gives `owner`, `repo`, and the PR number. These values override the other parameters. |
| `owner` | GitHub org or user name | From the URL, else required | The owner of the repository. Use the value of the user word for word. Never infer it. |
| `repo` | Repository name | From the URL, else required | The name of the repository. Use the value of the user word for word. Never infer it. |
| `interval` | `5m`, `15m`, `30m`, `1h`, `<N>m` | `15m` | The poll interval for `loop`. Without `loop`, the skill ignores it. |
| `loop` | flag | off | Turns on the monitor. After the first cycle, the skill starts `/loop` at `interval` (see Phase 6). Without this flag, the skill runs one cycle and stops. Not allowed together with `deep-fix` (see Rules). |
| `dry-run` | flag | off | Analysis and a report in chat only. No replies and no edits. |
| `tags` | Tag names, comma-separated, for example `ToFix,Question` | all | Process only these tags in this cycle. Write the tag names without brackets. |
| `bots` | Bot logins, comma-separated | `github-actions[bot]`, `copilot-pull-request-reviewer[bot]`, `coderabbitai[bot]` | Adds bot logins to the default bot list. Phase 2 step 1 keeps the comments of listed bots and skips the comments of other bots. It compares logins without the `[bot]` suffix. A comment with an automated-review header goes to Phase 3b, from any author. |
| `no-reply` | flag | off | Post no thread replies. Code edits are still allowed. |
| `no-edit` | flag | off | Drafts only. Never edit files, also not for a trivial fix. |
| `no-commit` | flag | off | Edit and stage locally only. Do NOT commit or push. For a review session where the human wants to inspect the change first. |
| `squash` | flag | off | One commit for all fixes of this cycle, instead of one commit for each thread. The push stays once per cycle, and it still needs the go-ahead unless `autonomous` is set. |
| `autonomous` | flag | off | No gate of this skill stops: Bucket A1, Bucket A2, and the push go-ahead (see "Autonomy"). The skill posts `[Question]` and `[ToDiscuss]` replies. It implements fixes where nothing settles the approach, and automated-review fixes that add a new architecture or a new public contract. It creates `[OutOfScope]` issues through Task Composer. It pushes once per cycle. The invariants of Bucket B and an active "pause for my review" instruction still hold. `--autonomous` also works. On a `deep-fix` run, pass `--autonomous` to `/research-implement-review-report`. |
| `interactive` | flag | off | Stop at the gates of Bucket A1 and Bucket A2 (see "Autonomy"). `--interactive` also works. On a `deep-fix` run, pass `--interactive` to `/research-implement-review-report`. |
| `strict` | flag | off | Pause before every file edit, whatever its size. |
| `include-resolved` | flag | off | Also process the threads that Phase 2 skips because `is_resolved` or `is_outdated` is true. Rarely useful. |
| `deep-fix` | `<commentId>` or `T#<commentId>` | off | The ID of the top comment of the thread (the `T#` number), not the `PRRT_` node ID. Send the fix of this ONE thread through `/research-implement-review-report` with `--commit-mode=single`, instead of the inline fix path of this skill. That command runs research, a plan, a plan gate, the implementation, a review loop, and a report. A human named the thread, so no size or tag list limits it. Only the ineligible cases in `references/deep-fix.md` apply. One thread per invocation. Not allowed together with `loop` (see Rules). |
| `deep-fix-rounds` | `<N>` | `2` | The cycle count of the review loop, passed word for word as `--rounds` to `/research-implement-review-report`. Without `deep-fix`, the skill ignores it. |

## Workflow

### Dispatch model — two stages by default, two models

Each cycle runs as **two** one-shot, unnamed subagent dispatches, never one. Stage 1 does the mechanical extraction, and Stage 2 does the work that needs judgment. Different work gets its own dispatch. See `dev-essentials:subagent-orchestration` Rule 1 (each logical work unit goes to a subagent) and Rule 4 (GitHub MCP work goes to a subagent by default). If `deep-fix` names an eligible thread, the cycle also runs Stage 3 and Stage 3b. These stages are opt-in additions to the two stages, not a replacement (see `references/deep-fix.md`).

| Stage | Model | Phases | Mandate |
| --- | --- | --- | --- |
| **Stage 1: classifier** | **Haiku** | Phase 1 and Phase 2 | **Read-only**. Fetch the threads, drop the noise, classify, find the committed-fix state again, and return the Stage 1 report. No GitHub writes and no file edits. No git writes to the working tree, the index, or the history. `git fetch` is expected. No verdicts and no replies. |
| **Stage 2: actor** | **Sonnet** | Phase 3, 3b, and Phase 4 steps 1 to 4. After the push of the orchestrating session, the resolve step of Phase 4 and Phase 5. On a `deep-fix` cycle: Phase 3, 3b, and Phase 4 steps 1 to 4 only. | The Stage 1 report is its only source of thread data. Every judgment call, code edit, commit, reply, and resolve happens here. The one exception is the `deep-fix` thread, which Stage 2 hands off. On a `deep-fix` cycle, Stage 2 ends after Phase 4 step 4, before the push (see `references/deep-fix.md`). Stage 2 never runs `git push`. |
| **Stage 3: deep-fix** (opt-in, `deep-fix` only) | *The orchestrating session itself, not a subagent dispatch* | `references/deep-fix.md` | Runs `/research-implement-review-report` with `--commit-mode=single` as its own next phase. That command can stop on a question, and with `interactive` on its Phase 1 sign-off gate. Questions and that gate belong to the session that talks to the user. |
| **Stage 3b: deep-fix reply** | **Sonnet** | `references/deep-fix.md` | A one-shot GitHub dispatch (Rule 4). It posts the thread reply after Stage 3 reports its squash SHA, its review-loop stop verdict, and its round count. It does not resolve the thread. |

Stage 1 does the mechanical extraction that the Haiku tier covers: tag matching, thread-state filters, and git ancestry checks. Stage 2 does judgment work, which needs the judgment tier (see "Model selection" in `dev-essentials:subagent-orchestration`).

**Who talks to the user**. Subagents do not talk to the user. The orchestrating session asks every question and owns every stop that waits for an answer. It runs these steps itself: Phase 1 steps 2, 5, and 6, and the push of the cycle with its go-ahead. It also runs Phase 6, Stage 3, and the question of Phase 2 step 5 for an `unconfirmed-commit-claim` thread. A Stage 2 step can need an answer of the user. Examples: a `[Question]` draft, a Bucket A2 draft, and an edit under `strict`. Then Stage 2 records the open item and goes on with the other threads. It returns all open items at the end of its work. The orchestrating session asks the user. It sends the answer to the same Stage 2 agent with `SendMessage`. Stage 2 then finishes the open items of the same task (`dev-essentials:subagent-orchestration` Rule 5).

**Who pushes**. Stage 2 never runs `git push`. It returns after Phase 4 step 4 of every thread, with its commit SHAs. The orchestrating session asks for the go-ahead (unless `autonomous` is set) and pushes once. Then it resumes the same Stage 2 agent with `SendMessage` for the resolve step of Phase 4 and for Phase 5. If the push does not happen (no go-ahead, or the user declines), resume the same Stage 2 agent for Phase 5 only. It runs no resolve step. On a `deep-fix` cycle, the orchestrating session keeps the resolve and Phase 5 (see `references/deep-fix.md`).

**What Stage 2 returns about `processedCommentIds`**. At the end, Stage 2 also returns the `processedCommentIds` entries (`references/thread-state-schema.md` § "`processedCommentIds`") of the comments that it completed or explicitly skipped. The orchestrating session adds them to its set.

**Briefing the stages**. Each brief gives the absolute path of the skill folder, `${CLAUDE_SKILL_DIR}`. It names the files that the stage reads: this `SKILL.md` and the reference files of its phases (see "Supporting files"). `processedCommentIds` and the PR metadata cache live in the orchestrating session, not in a dispatch. Pass both into each Stage 1 brief, with every invocation parameter (`tags`, `bots`, `include-resolved`, `dry-run`, and the others). Stage 1 returns `prMetadata` in its report. Stage 1 must STOP at each ask-the-user branch of Phase 1, and report it in the `blockers` list of the report. It never picks an option silently. These branches are: `owner` or `repo` not given and not in a URL, the target PR not found, and MCP not available. In Phase 2, a failed fetch of the PR head ref is one more blocker (see `references/thread-state-schema.md` § "Ancestry check").

**Stage 1 deliverable**. Stage 1 returns the Stage 1 report of [references/thread-state-schema.md](references/thread-state-schema.md) § "Stage 1 report". The report has one entry for each active thread. Each entry has the comment text word for word, the T# link, and the `assessedState` of Phase 2 step 5. It also has the flag for a newer human reply, and candidate override phrases of the reviewer. The report also has a `summary` block for the cycle. The orchestrating session can report from it at once, without a wait for Stage 2.

**Two results of a read-only Stage 1**:

- The `cured` branch of Phase 2 step 5 is the one GitHub write in Phase 2 (the catch-up resolve). Stage 1 only derives and reports that verdict. **Stage 2 tests it again first, and makes the write as its first action, before Phase 3**. Stage 2 runs the ancestry check itself (see `references/thread-state-schema.md` § "Ancestry check") against `origin/pull/<prId>/head`, with the `claimedSha` field of the report. No new MCP call is needed. If its result agrees with the report, Stage 2 makes the catch-up resolve. This keeps the order of step 5: the catch-up comes before Phase 3 and Phase 4 of this cycle. If its result disagrees, Stage 2 does NOT resolve the thread, and handles it as `unconfirmed-commit-claim`. A premature resolve misleads a human reviewer. For the same reason, the resolve step of Phase 4 always runs the ancestry check again (against another target ref).
- The `unconfirmed-commit-claim` branch of step 5 asks the human a question. Stage 1 reports the state in its report, and the orchestrating session asks the question.

**What Stage 2 can still call**. Stage 2 does NOT call `pull_request_read` `method: get_review_comments` again, because Stage 1 already did that work. Stage 2 makes only the calls that Stage 1 had no reason to make: `mcp__plugin_github_github__add_reply_to_pull_request_comment`, `mcp__plugin_github_github__pull_request_review_write` (`method: resolve_thread`), and the extra context that the judgment on one thread needs. The main case is Phase 3b steps 1 and 2: read the real code, and widen the lens. Stage 1 did not do this, because it sets no verdicts. Two exceptions allow a new fetch:

- The file or line context of a thread in the report is STALE or CONTRADICTORY. Then Stage 2 can fetch the current data of that one thread. Do not guess. This exception does not cover `filePath: null`, which is normal for a PR-level summary banner of an automated review.
- `add_reply_to_pull_request_comment` reports a failure for a reply. Then find out whether the reply landed before you retry (`dev-essentials:github-mcp-conventions` Rule 4). A blind retry posts a duplicate. If the reply is there, treat the action as done. Do not retry, and do not leave it for the next cycle. If the reply is not there, post it again.

**Under `dry-run`:** both stages run. Stage 2 reads code, sets the automated-review verdicts, and writes the drafts for the dry-run report. It makes no GitHub write, no edit, and no commit.

**Under `loop` (Phase 6):** each cycle runs Stage 1 and Stage 2 again from the start. Never cache the Stage 1 report across cycles, because thread state changes between cycles. Only `processedCommentIds` and the PR metadata cache carry over, and the orchestrating session holds them.

### Phase 1 — Session bootstrap (once per `/loop` session)

1. Find out whether the `mcp__plugin_github_github__*` tools are available. If they are missing, stop and ask the user to reconnect them with `/mcp`.
2. Orchestrating session: if the invocation has both `deep-fix` and `loop`, STOP and ask the user which one they meant (see Rules). Do not guess, and do not drop either flag silently.
3. Resolve the target PR:
   - For a full GitHub URL in `pr`, parse `owner`, `repo`, and the PR number from the URL. Call `mcp__plugin_github_github__pull_request_read` with `method: get` and these values, to find out whether the PR exists.
   - For a number in `pr`, `owner` and `repo` are required. Call `mcp__plugin_github_github__pull_request_read` with `method: get`, `owner`, `repo`, and `pullNumber`.
   - If `owner` or `repo` is missing and no URL holds it, STOP and ask the user before any call. Never infer it from the git remote or from the session context.
4. Cache the PR metadata from the `pull_request_read` response: `title`, `state`, `html_url`, and `number`. Also cache the head branch as `headRefName` (from `head.ref`) and the base branch as `baseRefName` (from `base.ref`). The ancestry checks do not use `origin/<headRefName>`, because a PR from a fork has no such branch on `origin`. They use `origin/pull/<prId>/head` (see `references/thread-state-schema.md` § "Ancestry check").
5. Orchestrating session: start an in-memory `processedCommentIds` set (see [references/thread-state-schema.md](references/thread-state-schema.md)).
6. Orchestrating session: print a one-line session header: the PR number, the title, the resolved `interval`, and the monitor mode (`one-shot` or `loop <interval>`).

### Phase 2 — Fetch and classify (every cycle)

**Fetch the review comments** with `mcp__plugin_github_github__pull_request_read` and `method: get_review_comments`. The method returns the review threads of the PR. Each thread has the state fields `is_resolved`, `is_outdated`, and `is_collapsed`, its node ID (`id`), and its comments. Phase 4 needs the node ID for `resolve_thread` and `unresolve_thread`, and it is not a comment ID. The method uses cursor pagination: pass `perPage` (at most 100), and pass the `endCursor` of the previous page as `after`. Follow `dev-essentials:github-mcp-conventions` Rule 3. Never stop after the first page. Stop at a page that gives no further `endCursor`, or that has fewer items than `perPage`.

**Drop the noise before you classify:**

1. Skip each comment of a bot that is not in the bot list. The default list is `["github-actions[bot]", "copilot-pull-request-reviewer[bot]", "coderabbitai[bot]"]`, and the `bots` parameter adds to it. `get_review_comments` can return a bot login without the `[bot]` suffix, for example `copilot-pull-request-reviewer`. So compare each login with the list without that suffix. One exception: a bot comment with an automated-review header goes to Phase 3b (see step 4).
2. **Filter by the real thread state**. Unless `include-resolved` is set, skip each thread with `is_resolved: true` or `is_outdated: true`. Do this before any work on classification, so that a resolved or outdated thread never costs a reply. `is_outdated` means that the original diff position of the thread no longer exists, because later commits moved past it. Its comment can still be open, but the code that it pointed to is gone. So the skill skips it by default, like a resolved thread.
3. Build an in-memory **active roster** with one entry for each remaining thread: `{id, threadNodeId, isResolved, isOutdated, state, commentCount, lastAuthor, lastContent, filePath, line, html_url}`. The roster keys `isResolved` and `isOutdated` hold the `is_resolved` and `is_outdated` values of the thread. `threadNodeId` holds the `id` of the thread. The roster `id` is the ID of the top comment of the thread. Phase 4 needs `threadNodeId` for the resolve call. To read the source file in Phase 3 or Phase 3b, use `Read` with `offset: line-10, limit: 30`. A read of the whole file wastes tokens, and it adds the reminder of each `.claude/rules/*.md` file.

**Classify each comment:**

4. For each comment that is NOT in `processedCommentIds`:
   - Find out whether the comment is a reply of Claude. A reply of Claude starts with `**[AI]**` or `**[AI][Draft]**` (bold form), or with `[AI]` or `[AI][Draft]` (old plain form). Skip such a comment, and do NOT classify it.
   - A comment whose first non-empty line is an automated-review header goes to Phase 3b. Examples: `AI Code Review`, `copilot:review`, or a similar heading from a bot.
   - For other comments, parse the leading tags: the brackets at the very start, for example `[ToFix][Performance]`. Several tags combine.
   - A comment with no known tag counts as `[Note]`.
   - If `tags` is set and no parsed tag is in it, skip the comment. Do NOT add it to `processedCommentIds`.

5. **Find the committed-fix state of each active thread again, in every cycle**. No state persists between cycles. Apply [references/committed-fix-state.md](references/committed-fix-state.md) to each thread of the active roster. The step looks for the newest reply of Claude with an affirmative commit claim, for example `Committed as <sha>`. It gives one of four outcomes:

   - `fresh-unhandled`: no `**[AI]**` or `**[AI][Draft]**` reply exists. Go on to Phase 3.
   - `already-assessed`: the newest such reply claims no commit. Leave the thread alone, unless a newer human reply exists.
   - `cured`: the claimed SHA is already an ancestor of `origin/pull/<prId>/head`. Resolve the thread as a catch-up step, unless `openFindingsMarker` is `true`.
   - `unconfirmed-commit-claim`: nothing shows yet that the commit claim is safe to report as ready. Ask the human, and implement nothing new on the thread. No flag skips this question, also not `autonomous`.

   A newer reply of a human after the commit claim stops every automatic catch-up action on the thread. The reference file has this guard, the report lines, and the rules for `dry-run` and `no-reply`.

### Phase 3 — Act per tag

Apply the matrix in [references/tag-actions.md](references/tag-actions.md) to each comment. It has the action, the reply, and the examples for each tag. The gates of the matrix follow "Autonomy": without `interactive`, the Bucket A1 gates do not stop, and only `autonomous` passes the Bucket A2 gates. A comment with an automated-review header goes to Phase 3b, whatever its tags. Reviewers write the tags in bold at the very start of the comment, for example `**[ToFix]**`. Use the same form for the tags in replies.

The size cut-off is your judgment, not a hard rule. About 20 lines, one file, and no public API change is only a guideline. It applies to `[ToFix]`, `[Performance]`, `[PX]`, and trivial `[Suggestion]`. It does not apply to the automated-review path (see Phase 3b step 5). A per-thread override of the reviewer always wins:

- `just fix it` or `no draft, apply directly`, in the thread or in chat: implement and commit, also where the default is a draft. The intent of the reviewer must be clear.
- `show me a draft first`, `don't commit yet`, or `let me see the diff`: draft only for that thread, also for a trivial change. Post `**[AI][Draft]**` and wait.

If you apply an override, say so in the reply, so that the trail is explicit.

#### `deep-fix` override

If `deep-fix` names a thread and the thread is eligible, the thread skips its normal action in the tag matrix, and goes to Stage 3. Read [references/deep-fix.md](references/deep-fix.md) before you act on that thread. The file has the eligibility rules and the list of ineligible cases.

### Phase 3b — Automated review verification

Automated review comments are often too narrow, false positives, or not applicable to production paths. Always test each one on your own before you reply. Read [references/automated-review-verification.md](references/automated-review-verification.md) first. It has the full list of steps, the verdicts, the obviousness test, and the draft templates.

Minimum steps:

1. Read the real code at the file path and the line range of the thread. Do not trust the quoted snippet.
2. Widen the lens: the enclosing method, its callers, the related tests, the DI composition, and the feature-flag guards.
3. Set the verdict: `valid`, `valid-but-narrow`, `needs-clarification`, `false-positive`, or `not-applicable`.
4. Set the confidence: `high`, `medium`, or `low`.
5. **Obviousness test, only for `valid` and `valid-but-narrow`**. The full test is in `automated-review-verification.md` § "Obviousness test". The size of the fix does not matter. A fix that meets these three conditions gets a direct implementation:
   - It does not rewrite the target file or section from scratch, and it is not a redesign of the same size.
   - It stays inside the files and areas that the PR diff already touches.
   - It adds no NEW architecture and no NEW public contract.

   A confidence below `high` does not stop the fix. Implement your best fix, and state the open question in the chat report and in the reply (**ask AND fix**). For a fix that meets the conditions, treat the finding like `[ToFix]`: implement, commit (Phase 4), and post a non-draft `**[AI]**` "Implemented fix" reply. This path has no draft stage. For a fix that fails a condition, go to step 6. With `autonomous`, implement two kinds of these fixes, as Bucket A2 says. The first is a fix at the rewrite-from-scratch exception that stays inside the PR diff. The second is a fix that fails the third condition but meets the second. If `deep-fix` names the thread, a fix at rewrite-from-scratch size goes to Stage 3 instead (the second exit, see [references/deep-fix.md](references/deep-fix.md)). `needs-clarification`, `false-positive`, and `not-applicable` NEVER take this path. For them, go to step 6.
6. Post a `**[AI][Draft]**` reply with one of the verdict templates in `references/automated-review-verification.md`. Each template ends with `*Draft pending author confirmation.*`. Keep this closing line.
7. Report the draft to the human (see "Who talks to the user"). Do NOT edit code. Wait for approval before you implement.

### Phase 4 — Commit, reply, push, then flag for resolution

Phase 4 runs in Stage 2, except the push, which the orchestrating session runs (see "Who pushes"). Read [references/commit-push-resolve.md](references/commit-push-resolve.md) before the first commit of the cycle. It has the full steps, the reply templates, and the rules for thread resolution. In short, for each thread that this cycle fixes:

1. **Build and test**: build the affected projects and run the affected tests. If the build fails or a test regresses, do NOT commit.
2. **Stage**: `git add` only the files of this thread. Never `git add -A` or `git add .`.
3. **Commit**: one commit for each thread by default, with the subject `PR #<prId> T#<commentId>: <short imperative summary>`. `squash` makes one commit at the end of the cycle. `no-commit` skips the commit and the push.
4. **Reply**: post the reply with the LOCAL commit SHA. The reply does not claim a push.

Then, once per cycle:

- **Push**: the orchestrating session runs one `git push` for all commits of the cycle, after steps 1 to 4 ran for every thread. It needs the go-ahead of the user (see Rules), unless `autonomous` is set.
- **Resolve threads and report**: after the push lands, run the ancestry check for each thread that this cycle fixed, and resolve it. Without a landed push, resolve nothing.

The reply comes early and the resolve comes late. The reply claims only a local commit. The resolve tells the reviewer that the fix is visible, and that is true only after the push.

#### Stage 3 — `deep-fix` brief and outcomes

On a cycle with an eligible `deep-fix` thread, that thread skips steps 1 to 4. Stage 2 ends after step 4 of the other threads, before the push, and hands back to the orchestrating session. The orchestrating session runs Stage 3, dispatches Stage 3b, and owns the push, the resolve, and Phase 5 of that cycle. The brief, the hand-back, the replies, and the `stop-blocked` path are in [references/deep-fix.md](references/deep-fix.md).

#### Reply templates and thread resolution

Every reply starts with `**[AI]**` or `**[AI][Draft]**` and a linked `**[[T#<commentId>](<html_url>)]**` tag on the first line. Take the link from the `html_url` field that `pull_request_read` returns. Never build a URL by hand (see `dev-essentials:github-mcp-conventions` § "Thread anchors and `html_url`"). The templates, the `no-reply` split, and the lists of threads to resolve and never to resolve are in [references/commit-push-resolve.md](references/commit-push-resolve.md). For the tone and the length of a reply, follow [references/review-principles.md](references/review-principles.md).

### Phase 5 — Cycle log

After each cycle, print the cycle log of [references/thread-state-schema.md](references/thread-state-schema.md) § "Cycle log", with one line for each thread. Also:

- With `squash`, replace the commit SHAs of the threads with one line at the end: `Cycle commit a1b2c3d (T#12, T#14, T#18).` With `no-commit`, replace the SHA part with `staged locally`.
- Always end the log with a line about the push state. Then the user always knows whether the reviewer can see the fixes. Write `N commits ready, not yet pushed — push when ready` while the commits wait for the go-ahead. Write `N commits pushed as <sha(s)>` after the push landed (after the go-ahead, or with `autonomous`).
- With `autonomous`, put a `Decisions for your review` list before the line about the push state. This list is the final-report list of "Autonomy". Give one line for each decision that `autonomous` made in this cycle without a stop (Bucket A2):
  - The approach or the direction that you chose for a `[ToFix]`, `[Suggestion]`, or `[Optional]` thread where nothing settled it.
  - An automated-review fix at the rewrite-from-scratch exception.
  - An automated-review fix that adds a new architecture or a new public contract.

  Use this form: `T#<commentId> <file>:<line>: <the decision>. Reason: <one line>.` A cycle with no such decision has no list.
- A thread whose reply is live but whose commit is not pushed shows `reply posted, pending push`. It stays open until its push lands (see Phase 4).
- On a `deep-fix` cycle, the orchestrating session prints this log, not Stage 2. See [references/deep-fix.md](references/deep-fix.md) for the rows.

Stage 2 reports a comment ID as processed only after its action, or an explicit skip, completed without error. The orchestrating session then adds it to `processedCommentIds`. After a failure, leave the comment unprocessed, so that the next cycle tries again.

### Phase 6 — Loop and pause

Phase 6 runs in the orchestrating session. The default is **one-shot**, and the monitor is opt-in.

1. **No `loop` flag and no outer `/loop` (default)**: exit after the first cycle. Announce: `Monitoring skipped (one-shot default). Pass 'loop' to start polling.`
2. **The skill already runs inside `/loop`**: return control to `/loop`. It sleeps and invokes the skill again. Do NOT start a nested `/loop`.
3. **`loop` flag on a standalone invocation**: at the end of the first cycle, start the monitor:

   ```text
   /loop <interval> /process-pr-comments pr=<id> owner=<owner> repo=<repo> [other original params except 'loop', 'deep-fix', and 'deep-fix-rounds']
   ```

   Pass on every parameter of the user except `loop`, `deep-fix`, and `deep-fix-rounds`. The inner invocation runs under `/loop`, so it does not need `loop`. `deep-fix` is not allowed with `loop` (see Rules), so the new invocation drops it. Pass on `interactive` and `autonomous`, so that each monitor tick runs in the same mode. `interval` is the resolved value (default `15m`). Announce the change: `Entering monitor mode: /loop <interval>.`

If the PR becomes `closed` or `merged` in any cycle, stop the loop and tell the user.

## Stalemate detection

Count the exchanges between Claude and the reviewers in the full history of the thread, not only in this session. An exchange is a reply with the `**[AI]**` prefix (also the old plain `[AI]` form) and the reply of a reviewer after it. Do NOT count the replies of the author that are not AI replies. The author can add context, and that is not a stalemate.

If the count is over 3 AND the last two replies show an open disagreement, stop the automatic replies. Show the thread to the human in chat with this suggestion: "Consider escalation, a design review, or talking this out synchronously."

## Supporting files

| File | Who reads it, and when |
| --- | --- |
| [references/tag-actions.md](references/tag-actions.md) | Stage 2, before it acts on a tagged comment. The full matrix for each tag, with examples. |
| [references/review-principles.md](references/review-principles.md) | Stage 2 and Stage 3b, before they write a reply. |
| [references/automated-review-verification.md](references/automated-review-verification.md) | Stage 2, before it sets a verdict or drafts a reply to an automated review comment. |
| [references/thread-state-schema.md](references/thread-state-schema.md) | Stage 1 and the orchestrating session: the dedup state, the PR metadata, the Stage 1 report, the ancestry check, and the cycle log. Stage 2, for the ancestry check and the cycle log. |
| [references/committed-fix-state.md](references/committed-fix-state.md) | Stage 1, for Phase 2 step 5. Stage 2, for the `cured` and `unconfirmed-commit-claim` threads. |
| [references/commit-push-resolve.md](references/commit-push-resolve.md) | Stage 2, before the first commit of a cycle (Phase 4). Stage 3b, for the reply templates. |
| [references/deep-fix.md](references/deep-fix.md) | The orchestrating session and Stage 2, for a `deep-fix` run. Stage 3b, for its replies. |

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
