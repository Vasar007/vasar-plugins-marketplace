---
name: process-pr-comments
description: Process GitHub pull-request review comments as the PR author, using the review-tag taxonomy ([ToFix], [Optional], [Suggestion], [Question], [ToDiscuss], [Performance], [OutOfScope], [Note], [PX], [Repetition]) and the special automated-review header. Classifies every non-resolved comment, implements small fixes, drafts larger ones, re-verifies automated review proposals before replying, delegates issue creation to Task Composer, and posts [AI]-prefixed replies without resolving threads. Runs once by default; opt in to a polling monitor with the `loop` flag (default cadence 15m). Triggers on requests like "process PR comments", "work through review feedback", "handle GitHub PR comments", "respond to reviewers", "address review comments", "monitor PR for new comments", or a GitHub PR URL with a request to act on its feedback.
---

# Process PR Review Comments

## Purpose

Acts on review comments **as the PR author**. Classifies each non-resolved comment by its review tag, applies a tiered response workflow (implement small fixes, draft larger ones, answer questions, delegate tracking issues), and posts a concise `**[AI]**`-prefixed reply (Markdown bold, matching the reviewer convention of bolding leading tags like `**[ToFix]**`) so reviewers can distinguish Claude's responses from the author's. Thread resolution is always left to a human.

## When to use

- User asks to process, work through, or address PR review comments.
- User pastes a GitHub PR URL or a PR number and asks for comment handling.
- User wants a recurring monitor ("every 15 minutes check for new comments").
- Automated review bots (e.g., GitHub Actions, Copilot, CodeRabbit) have commented on the PR and the user wants verified, drafted responses.

## When NOT to use

- Reviewing code written by someone else — that is the reviewer side, handled by other workflows.
- Creating a PR, editing its description, changing reviewers.
- Resolving threads — always a human decision; do not invoke any resolve tool.

## Prerequisites

1. GitHub MCP tools (`mcp__plugin_github_github__*`) must be available. If missing, stop and ask the user to reconnect via `/mcp` before retrying (see `dev-essentials:github-mcp-conventions` Rule 5).
2. The user must supply the explicit **`owner`** and **`repo`** pair (or a full GitHub PR URL from which they can be parsed). Never infer from git remote or session context (see `dev-essentials:github-mcp-conventions` Rule 1).
3. The Task Composer agent (`task-composer` from `dev-essentials`) must be loaded when an issue needs to be created for `[OutOfScope]` comments.

## Parameters

Accept free-form `key=value` pairs and standalone flags from skill args. All are optional except where noted.

| Param              | Values                                           | Default                     | Meaning                                                                                                                                                |
|--------------------|--------------------------------------------------|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `pr`               | `<id>` or full GitHub PR URL                     | Required                    | Target PR. A full URL supplies `owner`, `repo`, and `pullRequestNumber`; those override other params.                                                  |
| `owner`            | GitHub org or username                           | Parsed from URL or required | Repository owner. Must be supplied verbatim — never inferred.                                                                                          |
| `repo`             | Repository name                                  | Parsed from URL or required | Repository name. Must be supplied verbatim — never inferred.                                                                                           |
| `interval`         | `5m`, `15m`, `30m`, `1h`, `<N>m`                 | `15m`                       | Polling cadence when `loop` is set. Ignored otherwise.                                                                                                 |
| `loop`             | flag                                             | off                         | Opt IN to monitoring — after the first cycle, auto-enter `/loop` at `interval` (see Phase 6). Without this flag the skill runs a single pass and stops. |
| `dry-run`          | flag                                             | off                         | Analyze and report in chat only. No replies, no edits.                                                                                                 |
| `tags`             | comma-separated tag names, e.g. `ToFix,Question` | all                         | Process only these tags this cycle. Tag names match without brackets.                                                                                  |
| `no-reply`         | flag                                             | off                         | Do not post thread replies; code edits still allowed.                                                                                                  |
| `no-edit`          | flag                                             | off                         | Draft-only; never edit files, even for trivial fixes.                                                                                                  |
| `no-commit`        | flag                                             | off                         | Edit and stage locally only — do NOT commit or push. Useful for review sessions where the human wants to inspect.                                      |
| `squash`           | flag                                             | off                         | Bundle all fixes from this cycle into one commit instead of one commit per thread. Still pushed unless `no-commit`.                                    |
| `strict`           | flag                                             | off                         | Pause before every file edit regardless of size.                                                                                                       |
| `include-resolved` | flag                                             | off                         | Also process resolved/closed threads. Rarely useful.                                                                                                   |

### Rules

- **One PR per invocation.** Re-invoke the skill to target a different PR.
- **Linked PRs are read-only context.** When a comment references another PR, the skill MAY read that PR's description, threads, or diff for context. It MUST NOT classify or act on comments belonging to any PR other than the target.
- **Commit and push after every implemented fix** — default is one commit per thread, then `git push`. Opt out with `no-commit`; bundle under one commit with `squash`. See Phase 4.

## Workflow

### Phase 1 — Session bootstrap (once per `/loop` session)

1. Confirm `mcp__plugin_github_github__*` availability. If missing, stop and ask the user to reconnect via `/mcp`.
2. Resolve the target PR:
   - `pr` is a full GitHub URL → parse `owner`, `repo`, `pullRequestNumber` from the URL. Verify by calling `mcp__plugin_github_github__pull_request_read` with those values.
   - `pr` is an integer → require `owner` and `repo` params; call `mcp__plugin_github_github__pull_request_read(owner, repo, pullRequestNumber)`.
   - If `owner` or `repo` is missing and cannot be parsed from a URL, STOP and ask the user before making any call. Never infer from git remote or session context.
3. Hydrate PR metadata from the `pull_request_read` response: `title`, `state`, `headRefName`, `baseRefName`, `html_url`, `number`.
4. Initialize an in-memory `processedCommentIds` set (see [references/thread-state-schema.md](references/thread-state-schema.md)).
5. Print a one-line session header reporting the PR number, title, resolved `interval`, and monitoring mode (`one-shot` or `loop <interval>`).

### Phase 2 — Fetch and classify (every cycle)

**Fetch review comments** using `mcp__plugin_github_github__pull_request_read`, which returns the PR's review threads. For PRs with many comments, paginate with `per_page=30` per `dev-essentials:github-mcp-conventions` Rule 3.

**Pre-filter noise BEFORE classifying:**

1. Skip any comment authored by a bot not in the user-configured list. Default bot list: `["github-actions[bot]", "copilot[bot]", "coderabbitai[bot]"]`. The user may extend this list via the `bots` param. Bot comments routed through the automated-review path (Phase 3b) are an exception — they are still processed there.
2. Filter by thread state:
   - Default: keep active/unresolved threads. Skip resolved threads unless `include-resolved` is set.
3. Build an in-memory **active roster**: `{id, state, commentCount, lastAuthor, lastContent, filePath, line}` per active thread.

**Classify each comment:**

4. For each comment NOT in `processedCommentIds`:
   - Check if the comment is Claude's own reply: match `**[AI]**` or `**[AI][Draft]**` (bold form) or `[AI]` / `[AI][Draft]` (legacy plain form) at the start of the comment body. If matched, skip — do NOT classify.
   - If the comment contains an automated review header (`AI Code Review`, `AIR`, `copilot:review`, or similar bot-generated heading as the first non-empty line) → route to Phase 3b.
   - Otherwise parse leading tags (brackets at the very start, e.g. `[ToFix][Performance]`). Multiple tags combine.
   - No recognizable tag → treat as `[Note]`.
   - If `tags` param is set and no parsed tag intersects it → skip (do NOT add to `processedCommentIds`).

### Phase 3 — Act per tag

Apply the matrix in [references/tag-actions.md](references/tag-actions.md). Short summary:

Reviewer-facing tags are written as Markdown bold at the very start of the comment (e.g. `**[ToFix]**`). Match the same convention when referencing them in replies.

| Tag                                                 | Action                                                                                                                                                                                                                         |
|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `**[ToFix]**` / `**[Performance]**` / `**[PX]**`    | Small diff (< ~20 LoC, single file, no public API change) → implement, commit, push (see Phase 4), reply `**[AI]** Fixed: <summary>`. Larger → draft diff in chat, wait for approval.                                          |
| `**[Suggestion]**` / `**[Optional]**`               | Trivial → implement like `**[ToFix]**`. Otherwise → draft trade-off in chat, wait. Reply language respects the "optional" nature.                                                                                              |
| `**[Question]**`                                    | Draft the answer in chat, show it to the user, and post the `**[AI][Draft]**` reply ONLY after explicit user confirmation. Never post without confirmation.                                                                    |
| `**[ToDiscuss]**`                                   | Never implement. Summarize positions in chat and ask the user whether to draft a reply. Do NOT post a thread reply without that confirmation.                                                                                  |
| `**[OutOfScope]**`                                  | Never implement in this PR. If tracking requested → delegate to **Task Composer** agent to draft the issue; confirm with user; only then create the GitHub issue via `mcp__plugin_github_github__issue_write`. Reply `**[AI]** Tracked as issue #<id>`. |
| `**[Note]**` (and untagged)                         | Summarize in chat. No thread reply, no code edit, unless the human asks.                                                                                                                                                       |
| `**[Repetition]**`                                  | Handle as the underlying tag but ALSO surface the pattern: "Apply pattern fix across all N occurrences?"                                                                                                                       |
| Automated review header                             | Run Phase 3b. Never implement until the human approves.                                                                                                                                                                        |

The "small vs. large" cut-off is **your judgement call**, not a hard rule — ~20 LoC / single file / no public API change is only a guideline. Per-thread overrides from the reviewer always take precedence:

- **"Just fix it" / "no draft, apply directly"** in the thread (or in chat) → implement and commit even if you'd normally draft, provided the reviewer's intent is unambiguous.
- **"Show me a draft first" / "don't commit yet" / "let me see the diff"** → switch to draft-only for that thread even if the change is trivial. Post `**[AI][Draft]**` and wait.

When applying either override, mention it in the reply so the trail is explicit.

### Phase 3b — Automated review verification

Automated review comments are frequently too narrow, false-positive, or not applicable to production paths. Always verify independently before replying. Full checklist, verdict enum, and draft examples in [references/automated-review-verification.md](references/automated-review-verification.md).

Minimum steps:

1. Read the actual code at the thread's file path and line range. Do not trust the quoted snippet.
2. Widen the lens: enclosing method, callers, relevant tests, DI composition, feature-flag guards.
3. Decide verdict: `valid`, `valid-but-narrow`, `needs-clarification`, `false-positive`, or `not-applicable`.
4. Assign confidence: `high` / `medium` / `low`.
5. Post `**[AI][Draft]**` reply using one of the verdict templates in `references/automated-review-verification.md`. Every template ends with `*Draft pending author confirmation.*` — include this closing line.
6. Ping the human in chat. Do NOT edit code. Wait for approval before implementing.

### Phase 4 — Commit, push, and reply

After each implemented fix, do the following in order before moving to the next thread:

1. **Verify** — build the affected project(s) and run the affected tests. Do NOT commit if the build fails or any test regresses.
2. **Stage** — `git add` only the files touched by this specific thread. Never `git add -A` / `git add .`.
3. **Commit** — create one commit per thread (default). Message format:

   ```text
   PR #<prId> T#<commentId>: <short imperative summary>

   <1-3 lines explaining *why*, referencing the reviewer's point>

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   - If `squash` is set → accumulate all fixes from this cycle and create ONE commit at the end of the cycle with all `T#<id>` references listed in the body.
   - If `no-commit` is set → skip commit + push entirely; leave edits staged for the human.

4. **Push** — `git push` after each commit (or once at end-of-cycle for `squash`). Never force-push.
5. **Reply** via `mcp__plugin_github_github__add_reply_to_pull_request_comment` using the templates below. Thread resolution is NOT done automatically — ask the user to resolve via the GitHub UI if desired.

Splitting commits when one file covers multiple threads:

- For files touched by more than one thread, reset the file to `HEAD` after capturing the final state, then re-apply each thread's edit and commit it before moving to the next.

Bundle threads that share one pattern:

- When three-plus threads carry the **same reviewer note** applied at different call sites, treat them as one logical fix with one commit and reply on each thread pointing at the shared SHA.

Reply templates:

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

- Implemented fix (committed + pushed) → `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nFixed: <one-line summary>. Committed as <short-sha> and pushed.`
- Implemented fix with `no-commit` → `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nFixed: <one-line summary>. Diff staged locally, awaiting your commit.`
- Issue created → `**[AI]** **[[T#<commentId>](<html_url>)]**\n\nTracked as issue #<id>: <title>.`
- Draft (automated review / Question / non-trivial Suggestion) → `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**\n\n<analysis>\n\n*Draft pending author confirmation.*`
- Optional suggestion declined or deferred → `**[AI][Draft]** **[[T#<commentId>](<html_url>)]**\n\nOptional — keeping current shape; happy to change if preferred. Reason: <one line>.`

Cross-thread references inside the body should use the same linked form — resolve the target comment's `html_url` from the Phase 2 roster. Never hand-build URLs.

Reply style rules (from [references/review-principles.md](references/review-principles.md)):

- Frame as a request or statement of fact, not a command.
- Prefer "we" over "you".
- Tie judgement to a principle (SRP, naming, perf budget, invariant) rather than preference.
- Keep replies to ≤ 3 short lines unless the reviewer asked for depth.

Never claim a thread is resolved. Thread resolution is always a human action via the GitHub UI.

### Phase 5 — Cycle log

After each cycle, print a compact table to the user:

```text
Cycle 3 @ 15:42 — PR #4421 (5 threads checked, 2 new comments)
  T#12 [ToFix]  Auth.cs:42           → fixed (2 LoC), commit a1b2c3d pushed | reply posted
  T#17 [AutoReview] Domain/User.cs:88 → verdict: false-positive              | draft posted, awaiting approval
  T#22 [Note]   README.md:3          → noted                                | no action
```

With `squash`, replace per-thread commit SHAs with a single end-of-cycle line. With `no-commit`, replace the SHA segment with `staged locally`.

Add a comment ID to `processedCommentIds` only AFTER its action completes successfully. On failure, leave it unprocessed so the next cycle retries.

### Phase 6 — Loop and pause

Default is **one-shot**; monitoring is opt-in.

1. **No `loop` flag and no outer `/loop` wrapper (default)** → exit after the first cycle. Announce: `Monitoring skipped (one-shot default). Pass 'loop' to start polling.`
2. **Already wrapped in `/loop`** → return control to `/loop`; it performs the sleep and re-invokes. Do NOT start a nested `/loop`.
3. **`loop` flag set on a standalone invocation** → at end of first cycle, auto-enter monitoring.

If the PR transitions to `closed` or `merged` during any cycle, stop the loop and tell the user.

## Stalemate detection

Count `**[AI]**`-prefixed reply + reviewer-response exchange pairs across the thread's full history. If that exchange count exceeds 3 AND the latest two replies show unresolved disagreement, stop replying automatically. Surface the thread to the human: "Consider escalation, a design review, or talking this out synchronously."

## Safeguards

- Do NOT touch code unrelated to the reviewer's comment (respect PR scope).
- Do NOT post replies when `dry-run` or `no-reply` is set.
- Do NOT implement edits when `dry-run`, `no-edit`, or `strict` is set; draft only.
- Do NOT commit or push when `dry-run` or `no-commit` is set.
- Do NOT amend, rebase, squash existing history, or force-push.
- Do NOT push to any branch other than the PR source branch.
- Do NOT invent issue fields when delegating to Task Composer — always confirm title and type with the user first.
- Do NOT reprocess a comment already in `processedCommentIds` within the same session.
- Do NOT call any GitHub MCP tool with inferred `owner` or `repo` — always pass user-supplied or URL-parsed values verbatim (see `dev-essentials:github-mcp-conventions` Rules 1–2).
- Do NOT attempt to resolve threads via MCP — GitHub MCP has no resolve tool; direct the user to resolve via the GitHub UI.

## Supporting files

| File                                                                                                  | When to read                                                                    |
|-------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
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

# Bundle all fixes from this cycle under a single commit, then push
/process-pr-comments pr=42 owner=Vasar007 repo=my-repo squash

# Already wrapped in /loop — outer harness controls cadence
/loop 15m /process-pr-comments pr=42 owner=Vasar007 repo=my-repo
```
