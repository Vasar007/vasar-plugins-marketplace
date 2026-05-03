---
name: process-pr-comments
description: Process Azure DevOps pull-request review comments as the PR author, using the review-tag taxonomy ([ToFix], [Optional], [Suggestion], [Question], [ToDiscuss], [Performance], [OutOfScope], [Note], [PX], [Repetition]) and the special AI Code Review / AIR header. Classifies every non-resolved comment, implements small fixes, drafts larger ones, re-verifies AIR proposals before replying, delegates work-item creation to Task Composer, and posts [AI]-prefixed replies without resolving threads. Runs once by default; opt in to a polling monitor with the `loop` flag (default cadence 15m). Triggers on requests like "process PR comments", "work through review feedback", "handle ADO PR comments", "respond to reviewers", "address review comments", "monitor PR for new comments", or an Azure DevOps PR link with a request to act on its feedback.
---

# Process PR Review Comments

## Purpose

Acts on review comments **as the PR author**. Classifies each non-resolved comment by its review tag, applies a tiered response workflow (implement small fixes, draft larger ones, answer questions, delegate tracking work items), and posts a concise `**[AI]**`-prefixed reply (Markdown bold, matching the reviewer convention of bolding leading tags like `**[ToFix]**`) so reviewers can distinguish Claude's responses from the author's. Thread resolution is always left to a human.

## When to use

- User asks to process, work through, or address PR review comments.
- User pastes an Azure DevOps PR URL or a PR ID and asks for comment handling.
- User wants a recurring monitor ("every 15 minutes check for new comments").
- `AI Code Review` / `AIR` automation has commented on the PR and the user wants verified, drafted responses.

## When NOT to use

- Reviewing code written by someone else — that is the reviewer side, handled by other workflows.
- Creating a PR, editing its description, changing reviewers — use `PR Composer.agent.md`.
- Resolving threads — always a human decision, never invoke `repo_resolve_comment`.

## Prerequisites

1. Azure DevOps MCP tools (`mcp__azure-devops__*`) must be available. If missing, stop and ask the user to configure their Azure DevOps MCP server (e.g. `@azure/mcp-server-azuredevops`) before retrying.
2. The user's current working directory must be inside a git repository whose `origin` remote points at your Azure DevOps host (unless `pr` or `repo` parameters are set).
3. The Task Composer agent (`task-composer` from `dev-essentials`) must be loaded when a work item needs to be created for `[OutOfScope]` comments.

## Parameters

Accept free-form `key=value` pairs and standalone flags from skill args. All are optional.

| Param              | Values                                           | Default                     | Meaning                                                                                                                                                |
|--------------------|--------------------------------------------------|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `pr`               | `<id>` or full PR URL                            | Active PR on current branch | Target PR. A full URL supplies `organization`, `project`, `repo`, and `pullRequestId`; those override other params.                                    |
| `repo`             | repo name or ID                                  | Current git repo            | Source repo for the PR. Accepts any repo in the same ADO org.                                                                                          |
| `project`          | ADO project name                                 | Inferred from repo metadata | Scoping hint when a repo name is ambiguous across projects.                                                                                            |
| `interval`         | `5m`, `15m`, `30m`, `1h`, `<N>m`                 | `15m`                       | Polling cadence when `loop` is set or the skill is already wrapped in `/loop`. Ignored otherwise.                                                      |
| `loop`             | flag                                             | off                         | Opt IN to monitoring — after the first cycle, auto-enter `/loop` at `interval` (see Phase 6). WITHOUT this flag the skill runs a single pass and stops (default).  |
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

1. Confirm `mcp__azure-devops__*` availability. If missing, stop and ask the user to configure their Azure DevOps MCP server.
2. Resolve the target repo **to its GUID** (required — several `repo_*` tools do not accept a `project` parameter and fail on repo names):
   - `pr` is a full URL → parse `organization`, `project`, `repo`, `pullRequestId` from the URL, THEN call `mcp__azure-devops__repo_get_repo_by_name_or_id(repositoryNameOrId=<repo-name>, project=<project>)` to obtain the GUID.
   - Else if `repo` param is set → `mcp__azure-devops__repo_get_repo_by_name_or_id`. If the name matches repos in more than one project, call `repo_list_repos_by_project` for each candidate and ask the user to supply `project=<name>` before continuing. Never pick silently.
   - Else → derive repo from the current working directory's `origin` remote (call `repo_get_repo_by_name_or_id` on it). If that remote is not on your Azure DevOps host, ask the user before continuing.
   - Cache the resulting `repoGuid` for the whole session and pass it as `repositoryId` to every subsequent `repo_*` call. Do NOT pass the repo name.
3. Resolve the target PR inside that repo and hydrate metadata (always pass `repositoryId=<repoGuid>`, not the name):
   - `pr` is an ID (provided directly or parsed from the URL in step 2) → `mcp__azure-devops__repo_get_pull_request_by_id` to load `title`, `status`, `sourceRefName`, `targetRefName`, and the URL.
   - Else → `repo_list_my_branches_by_repo` + `repo_list_pull_requests_by_repo_or_project` with `sourceRefName` = current branch and status = `active`. On zero or multiple matches, ask the user which PR to target. Then call `repo_get_pull_request_by_id` on the chosen PR to hydrate metadata.
   - The hydrated metadata feeds the PR-metadata cache (see `references/thread-state-schema.md`) and the Phase 6 `completed` / `abandoned` check.
   - If `repo_get_pull_request_by_id` fails with "A project name is required in order to reference a Git repository by name" — you passed the repo name instead of the GUID. Resolve the GUID via `repo_get_repo_by_name_or_id` and retry.
4. Initialize an in-memory `processedCommentIds` set (see [references/thread-state-schema.md](references/thread-state-schema.md)). The set is session-local; a new `/loop` session starts fresh and relies on ADO thread state to avoid duplicate replies.
5. Print a one-line session header reporting the PR ID, title, resolved `interval`, and whether monitoring will auto-start at end of cycle (`monitor: one-shot` when neither `loop` nor an outer `/loop` wrapper is present (default), `monitor: /loop <interval>` when `loop` is set, `monitor: /loop <interval> (outer)` when the invocation is already wrapped in `/loop`). Monitoring is OPT-IN and is handled in Phase 6.

### Phase 2 — Fetch and classify (every cycle)

The PR's thread list is typically **80%+ noise** (`Microsoft.TeamFoundation.System` "ref updated" threads, one per push). Fetching and parsing them is the biggest token sink in this skill, so Phase 2 is structured in two stages: a cheap "roster" pass that identifies active thread IDs from trimmed payloads, and a targeted "context" pass that fetches file+line only for those IDs.

**Stage A — Roster pass (trimmed).**

1. `mcp__azure-devops__repo_list_pull_request_threads` for the **target** PR only, `fullResponse=false` (default), **`top=20`** (not 40 — 40 frequently overshoots the tool-result token cap on PRs with many pushes and triggers the save-to-file branch, which then costs you tokens a second time when you parse the saved file). Paginate via `skip` in 20-thread chunks. Threads fetched for any other PR (e.g., when reading a linked PR for context) MUST NOT advance to Phase 3 — discard them after reading.
2. Pre-filter the page to drop system-authored noise BEFORE classifying:
   - Skip any thread whose sole comment is authored by `"Microsoft.TeamFoundation.System"` — these are branch-update events produced by every push, not review content.
   - A helper identifier on a `fullResponse=true` response is `properties.CodeReviewThreadType == "RefUpdate"`; on trimmed output the only reliable signal is the author `displayName`. Either is sufficient.
3. Filter the remaining threads by status (trimmed payload uses **numeric** `status` codes, not strings — there is no `"status":"active"`):
   - Status enum: `0=unknown`, `1=active`, `2=fixed`, `3=wontFix`, `4=closed`, `5=byDesign`, `6=pending`.
   - Default: keep `1` (active) and `6` (pending). Skip `2`/`3`/`4`/`5` unless `include-resolved` is set.
   - Keep regardless of who replied last.
4. Build an in-memory **active roster**: `{id, status, commentCount, lastAuthor, lastContent}` per active thread. Do NOT request `threadContext` yet — the trimmed payload drops it, and chasing it now forces `fullResponse=true` over the whole list.

If the trimmed response still exceeds the cap after `top=20`, drop to `top=10`. **Do not** try to parse the saved-to-file JSON by writing scripts — re-issue the call with a smaller window. A `grep -ao 'status\\": 1' <saved-file> | wc -l` one-liner is fine to count actives without re-parsing.

**Stage B — Context pass (targeted full response).**

5. For each thread ID in the active roster that needs a file path (i.e., almost all of them), re-call `repo_list_pull_request_threads` with `fullResponse=true` on a narrow `skip`/`top` window that brackets the target IDs. Because thread IDs are roughly time-ordered, you can usually cover all actives with one or two `fullResponse=true` pages of `top=10–15`. Never call `fullResponse=true` over the whole PR — the per-thread JSON bloat (`_links`, `identities`, per-comment `_links`) is 3-5× the trimmed size and quickly blows the cap.
6. Record `threadContext.filePath` + `rightFileStart.line..rightFileEnd.line` next to each roster entry. When reading the source file in later phases, use `Read` with `offset: line-10, limit: 30` — reading the whole file is wasteful and also triggers per-file `.claude/rules/*.md` reminder injections, which add up.
7. For each comment NOT in `processedCommentIds` and NOT authored by Claude:
   - Claude's own replies are posted under the user's ADO identity (authenticated PAT) — so identity alone cannot distinguish author text from Claude's replies. Use the `**[AI]**` / `**[AI][Draft]**` prefix at the start of the reply body as the sole Claude-authored marker. For detection, match EITHER the bold form (`**[AI]**`, `**[AI][Draft]**`) OR the legacy plain form (`[AI]`, `[AI][Draft]`) at the start of the comment body, so threads replied to before the bolding convention are not re-processed. Do NOT filter by ADO identity, or the user's own non-AI comments will be suppressed.
   - If the comment contains `AI Code Review` or `AIR` as a header / first-line marker → route to the AIR verification branch (Phase 3b).
   - Otherwise parse leading tags (brackets at the very start, e.g. `[ToFix][Performance]`). Multiple tags combine.
   - No recognizable tag → treat as `[Note]`.
   - If `tags` param is set and no parsed tag intersects it → skip (do NOT add to `processedCommentIds` — a later cycle with different `tags` may revisit).
8. For each active thread that survives classification, `mcp__azure-devops__repo_list_pull_request_thread_comments` to get the full comment chain ONLY IF the trimmed payload from stage A truncated it (rare — trimmed keeps all comments). Skip this call when stage A already has the full chain.

### Phase 3 — Act per tag

Apply the matrix in [references/tag-actions.md](references/tag-actions.md). Short summary:

Reviewer-facing tags are written by the reviewer as Markdown bold at the very start of the comment (e.g. `**[ToFix]**`). Match the same convention when referencing them in replies Claude posts.

| Tag                                                 | Action                                                                                                                                                                                                                         |
|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `**[ToFix]**` / `**[Performance]**` / `**[PX]**`    | Small diff (< ~20 LoC, single file, no public API change) → implement, commit, push (see Phase 4), reply `**[AI]** Fixed: <summary>`. Larger → draft diff in chat, wait for approval.                                          |
| `**[Suggestion]**` / `**[Optional]**`               | Trivial → implement like `**[ToFix]**`. Otherwise → draft trade-off in chat, wait. Reply language respects the "optional" nature.                                                                                              |
| `**[Question]**`                                    | Draft the answer in chat, show it to the user, and post the `**[AI][Draft]**` reply ONLY after explicit user confirmation. Never post without confirmation.                                                                    |
| `**[ToDiscuss]**`                                   | Never implement. Summarize positions in chat and ask the user whether to draft a reply. Do NOT post a thread reply without that confirmation.                                                                                  |
| `**[OutOfScope]**`                                  | Never implement in this PR. If tracking requested → delegate to **Task Composer** agent to draft the work item; confirm with user; only then `mcp__azure-devops__wit_create_work_item`. Reply `**[AI]** Tracked as #<id>`.     |
| `**[Note]**` (and untagged)                         | Summarize in chat. No thread reply, no code edit, unless the human asks.                                                                                                                                                       |
| `**[Repetition]**`                                  | Handle as the underlying tag but ALSO surface the pattern: "Apply pattern fix across all N occurrences?"                                                                                                                       |
| `AI Code Review` / `AIR`                            | Run Phase 3b. Never implement until the human approves.                                                                                                                                                                        |

The "small vs. large" cut-off is **your judgement call**, not a hard rule — ~20 LoC / single file / no public API change is only a guideline. Per-thread overrides from the reviewer always take precedence:

- **"Just fix it" / "no draft, apply directly"** in the thread (or in chat) → implement and commit even if you'd normally draft, provided the reviewer's intent is unambiguous. The reviewer is explicitly waiving the draft checkpoint.
- **"Show me a draft first" / "don't commit yet" / "let me see the diff"** → switch to draft-only for that thread even if the change is trivial. Post `**[AI][Draft]**` and wait.

When applying either override, mention it in the reply (`**[AI]** Fixed per your "just fix it" direction: …` / `**[AI][Draft]** Draft per your request: …`) so the trail is explicit.

### Phase 3b — AIR verification

AIR comments are frequently too narrow, false-positive, or not applicable to production paths. Always verify independently before replying. Full checklist + verdict enum + draft examples in [references/air-verification.md](references/air-verification.md).

Minimum steps:

1. Read the actual code at the thread's `threadContext` file + line range. Do not trust the quoted snippet.
2. Widen the lens: enclosing method, callers, relevant tests, DI composition, feature-flag guards.
3. Decide verdict: `valid`, `valid-but-narrow`, `needs-clarification`, `false-positive`, or `not-applicable`.
4. Assign confidence: `high` / `medium` / `low`.
5. Post `**[AI][Draft]**` reply using one of the verdict templates in `references/air-verification.md`. Every template ends with `*Draft pending author confirmation.*` — include this closing line.
6. Ping the human in chat. Do NOT edit code. Wait for approval before implementing.

### Phase 4 — Commit, push, and reply

After each implemented fix, do the following in order before moving to the next thread:

1. **Verify** — build the affected project(s) and run the affected tests. Do NOT commit if the build fails or any test regresses.
2. **Stage** — `git add` only the files touched by this specific thread. Never `git add -A` / `git add .`.
3. **Commit** — create one commit per thread (default). Message format:

   ```text
   #<workItemId> PR <prId> T#<threadId>: <short imperative summary>

   <1-3 lines explaining *why*, referencing the reviewer's point>

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

   - If `squash` is set → accumulate all fixes from this cycle and create ONE commit at the end of the cycle with all `T#<id>` references listed in the body. Still one commit → one push.
   - If `no-commit` is set → skip commit + push entirely; leave edits staged for the human, and reply with the "staged" template below.

4. **Push** — `git push` after each commit (or once at end-of-cycle for `squash`). Never force-push. Never push to a protected branch other than the current PR source branch.
5. **Reply** via `mcp__azure-devops__repo_reply_to_comment` using the templates below.

Splitting commits when one file covers multiple threads:

- For files touched by more than one thread, reset the file to `HEAD` after capturing the final state, then re-apply each thread's edit and commit it before moving to the next. This keeps blame per-thread and makes individual fixes easy to revert. `git stash` + partial re-apply or `git checkout HEAD -- <file>` + Edit tool both work.

Bundle threads that clearly share one pattern:

- When three-plus threads carry the **same reviewer sentence** applied at different call sites (e.g. "Remove that, it is invalid because wrappers validate values during the construction." posted three times on three sibling files), treat them as one logical fix with one commit message and one commit, then reply on each thread pointing at the shared SHA. The `one commit per thread` default exists so blame stays per-thread — but when the threads are literally repetitions of each other, per-thread commits just inflate history without improving traceability. Use the skill's `**[Repetition]**` matrix entry as the tell: if you'd comment "Apply pattern fix across all N occurrences?" the answer here is yes.

Reply templates:

Every reply starts with a **leading tag section** — the `**[AI]**` (or `**[AI][Draft]**`) marker, optionally followed by other bold reviewer-style tags, and closed with a bold `**[T#<threadId>]**` thread tag **rendered as a clickable deep link to the thread** — all on the FIRST line. The body of the reply follows on the next paragraph. This mirrors how reviewers stack tags (`**[ToFix]** **[Performance]**`) and keeps the thread ID where the reader's eye already is, instead of orphaning it at the end of the message. ADO comments render Markdown, so the bold tags appear bold in the web UI and the link is clickable. The thread ID is the same numeric `id` returned by `repo_list_pull_request_threads` (Phase 2) — never a comment ID.

**Link format for the T# tag.** ADO's web UI uses the thread's `publishedDate` converted to **Unix epoch seconds** as the URL fragment. Compute it once per thread:

```text
<prWebUrl>                := <repository.webUrl>/pullrequest/<pullRequestId>
<threadAnchorSeconds>     := Math.floor(new Date(thread.publishedDate).getTime() / 1000)
<threadUrl>               := <prWebUrl>#<threadAnchorSeconds>
```

Verified example: thread `3096924`, `publishedDate = "2026-04-21T14:15:22.140Z"` → `1776780922` → URL
`https://<your-ado-host>/<collection>/<Project>/_git/<Repo>/pullrequest/<prId>#1776780922`.

Markdown syntax for the tag — the literal `[T#<id>]` must remain visible (including the brackets), so the double-bracket form puts a bracket-wrapped label inside a link and then bolds the whole thing:

```markdown
**[[T#<threadId>](<threadUrl>)]**
```

CommonMark: the outer `[` and `]` are literal characters; the inner `[T#<id>]` is the link label; `(<url>)` is the destination; the surrounding `**` bolds the visual result. Rendered: **\[T#3096924\]** (clickable).

Tag order on the first line:

```text
**[AI]** [optional auxiliary tags] **[[T#<threadId>](<threadUrl>)]**
<blank line>
<body>
```

Reply templates (the `\n\n` separates the leading tag line from the body — the T# tag is always a link):

- Implemented fix (committed + pushed) → `**[AI]** **[[T#<threadId>](<threadUrl>)]**\n\nFixed: <one-line summary>. Committed as <short-sha> and pushed.`
- Implemented fix with `no-commit` → `**[AI]** **[[T#<threadId>](<threadUrl>)]**\n\nFixed: <one-line summary>. Diff staged locally, awaiting your commit.`
- Work item created → `**[AI]** **[[T#<threadId>](<threadUrl>)]**\n\nTracked as work item #<id>: <title>.`
- Draft (AIR / Question / non-trivial Suggestion) → `**[AI][Draft]** **[[T#<threadId>](<threadUrl>)]**\n\n<analysis>\n\n*Draft pending author confirmation.*`
- Optional suggestion declined or deferred → `**[AI][Draft]** **[[T#<threadId>](<threadUrl>)]**\n\nOptional — keeping current shape; happy to change if preferred. Reason: <one line>.`
- Override applied ("just fix it") → first line stays `**[AI]** **[[T#<threadId>](<threadUrl>)]**`; body starts with `Per your "just fix it" direction: …` so the waiver is traceable.
- Override applied ("draft first") → first line stays `**[AI][Draft]** **[[T#<threadId>](<threadUrl>)]**`; body starts with `Draft per your request: …`.

Cross-thread references INSIDE the body should use the **same linked form** — e.g. `` "Same fix as **[[T#3093117](<thatThreadUrl>)]**" `` — so reviewers can jump between threads with one click. Resolve the target thread's `publishedDate` from the Phase 2 roster before composing the reply — do NOT hand-build anchors from the current time. If the referenced thread isn't in the roster, fall back to the plain bold `**[T#<id>]**` form rather than fabricating a URL.

Reply style rules (from [references/review-principles.md](references/review-principles.md)):

- Frame as a request or statement of fact, not a command.
- Prefer "we" over "you".
- Tie judgement to a principle (SRP, naming, perf budget, invariant) rather than preference.
- Keep replies to ≤ 3 short lines unless the reviewer asked for depth.

Never claim a thread is resolved. Never invoke `repo_resolve_comment` or any equivalent.

### Phase 5 — Cycle log

After each cycle, print a compact table to the user:

```text
Cycle 3 @ 15:42 — PR 4421 (5 threads checked, 2 new comments)
  T#12 [ToFix]  Auth.cs:42           → fixed (2 LoC), commit a1b2c3d pushed | reply posted
  T#17 [AIR]    Domain/User.cs:88    → verdict: false-positive              | draft posted, awaiting approval
  T#22 [Note]   README.md:3          → noted                                | no action
```

With `squash`, replace the per-thread commit SHAs with a single end-of-cycle line: `Cycle commit a1b2c3d (T#12, T#14, T#18) pushed.` With `no-commit`, replace the SHA segment with `staged locally`.

Add a comment ID to `processedCommentIds` only AFTER its action (or explicit skip decision) completes successfully. On failure, leave it unprocessed so the next cycle retries.

### Phase 6 — Loop and pause

Decide how the next cycle (if any) is scheduled. Default is **one-shot**; monitoring is opt-in.

1. **No `loop` flag and no outer `/loop` wrapper (default)** → exit after the first cycle. Announce: `Monitoring skipped (one-shot default). Pass 'loop' to start polling.`
2. **Already wrapped in `/loop`** (detected from the invocation context — the current call came from `/loop`'s re-invocation) → return control to `/loop`; it performs the sleep and re-invokes on the next tick. Do NOT start a second, nested `/loop`.
3. **`loop` flag set on a standalone invocation** → at end of first cycle, auto-enter monitoring by invoking the `loop` skill with:

   ```text
   /loop <interval> /process-pr-comments pr=<id> [other original params except 'loop']
   ```

   Forward every param the user supplied except `loop` (the inner invocation no longer needs it because it will run under `/loop`). The `interval` is the resolved value (default `15m`). Announce the transition: `Entering monitor mode: /loop <interval>.`

If the PR transitions to `completed` or `abandoned` during any cycle, stop the loop and tell the user.

## Stalemate detection

Count only the `**[AI]**`-prefixed replies (including the legacy plain `[AI]` form) paired with the reviewer's responses that followed them — i.e., back-and-forth exchanges between Claude and the reviewer(s) across the thread's full ADO history, not just the current session. The author's own non-AI replies are NOT counted (the author may legitimately add context without it being a stalemate).

If that exchange count exceeds 3 AND the latest two exchanged replies show unresolved disagreement, stop replying automatically. Surface the thread to the human in chat with the suggestion: "Consider escalation, a design review, or talking this out synchronously." This implements the mtlynch "avoid stalemates" principle.

## Safeguards

- Do NOT touch code unrelated to the reviewer's comment (respect PR scope).
- Do NOT post replies when `dry-run` or `no-reply` is set.
- Do NOT implement edits when `dry-run`, `no-edit`, or `strict` is set; draft only.
- Do NOT commit or push when `dry-run` or `no-commit` is set. Everything stays staged in the working tree.
- Do NOT amend, rebase, squash existing history, or force-push. Always create fresh commits.
- Do NOT push to any branch other than the PR source branch. Never push to `master`, `release/*` target branches, or any protected ref.
- Do NOT invent work item fields when delegating to Task Composer — always confirm title, type, priority with the user first.
- Do NOT reprocess a comment already in `processedCommentIds` within the same session.

## Supporting files

| File                                                                   | When to read                                                                    |
|------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [references/tag-actions.md](references/tag-actions.md)                 | Before acting on any tagged comment — full per-tag matrix with worked examples. |
| [references/review-principles.md](references/review-principles.md)     | Before composing replies — mtlynch distillation applied to the author's side.   |
| [references/air-verification.md](references/air-verification.md)       | Before drafting any `**[AI][Draft]**` reply to an AIR comment.                  |
| [references/thread-state-schema.md](references/thread-state-schema.md) | When initializing or updating the in-session dedup state and cycle log.         |

## Invocation examples

```text
# One-shot on current branch's active PR (DEFAULT — no flag needed)
/process-pr-comments

# Opt in to polling monitor at default 15m cadence
/process-pr-comments loop

# Polling monitor at 30m cadence
/process-pr-comments loop interval=30m

# Specific PR, different repo, 30-minute polling
/process-pr-comments pr=4421 repo=<OtherRepoName> loop interval=30m

# Full URL, one-shot
/process-pr-comments pr=https://<your-ado-host>/<collection>/<Project>/_git/<Repo>/pullrequest/4421

# Dry-run classification only, focus on [ToFix] and [Question]
/process-pr-comments dry-run tags=ToFix,Question

# Strict mode — nothing is edited without approval, with polling
/process-pr-comments loop strict

# Edit + stage only, no commit, no push (human will commit)
/process-pr-comments no-commit

# Bundle all fixes from this cycle under a single commit, then push
/process-pr-comments squash

# Already wrapped in /loop — outer harness controls cadence; do NOT also pass `loop`
/loop 15m /process-pr-comments
```
