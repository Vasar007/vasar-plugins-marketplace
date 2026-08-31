---
description: "Review a GitHub PR end-to-end — fetch metadata and diff, evaluate against repo conventions, render an HTML review artifact, and optionally post findings as new PR review comments"
argument-hint: "<pr-url> [--mode=html-only|post-all|post-<N>|post-<N>-<M>] [--orchestrate] | --multi <url1> <url2> ... [--orchestrate]"
---

Review the GitHub pull request: $ARGUMENTS

# Not a duplicate of `dev-essentials:review-loop`

`review-loop` already supports `target=pr <id>` end-to-end, ending in a verify-then-fix pass that **edits code**. Reach for it when the goal is "review and fix".

This command is for the other case — "review and report": evaluating a PR against conventions, producing a shareable HTML artifact, and optionally posting findings back as new PR review comments. It never edits the reviewed code, in either mode.

# Mode selection

Inspect `$ARGUMENTS` for the `--orchestrate` flag (anywhere after the URL):

- **Without `--orchestrate`** (default — "inline" mode): the main agent reads everything itself. Best for small PRs (< ~1,500 lines) where the full diff comfortably fits in context.
- **With `--orchestrate`** (delegation mode): the main agent dispatches subagents for the context-heavy steps (PR exploration, codebase/diff reading, convention evaluation, finding verification) and only keeps **synthesized findings + the specific lines referenced by those findings** in its own context. Best for large PRs (> ~2,000 lines, > 30 files), PRs touching many distinct areas, or when the user wants the main context preserved for follow-up work.

When `--orchestrate` is set, follow the **Orchestrator mode** section below instead of Phases 2–4. Phase 1 (setup), Phase 5 (HTML assembly), and Phase 6 (post comments) are the same in both modes. Phase 7 (multi-PR) is different in kind: it fans out one review subagent per PR **whether or not `--orchestrate` is set**, so `--orchestrate` has no top-level meaning there — it is forwarded into each per-PR subagent instead. See Phase 7.

# Workflow

## Phase 1 — Setup

Invoke `dev-essentials:github-mcp-conventions` via the `Skill` tool. Every rule in it applies here — most load-bearing for this workflow: Rule 1 (never infer `owner`/`repo` — pass the user-supplied values verbatim), Rule 2 (`owner` + `repo` on every call), Rule 3 (pagination discipline), Rule 4 (no comment edit/delete after posting — clean up via the GitHub UI), and Rule 5 (no REST/`gh`-CLI fallback).

Then invoke whichever convention skill(s) apply to the **target repo** — infer them from that repo's own `CLAUDE.md`, or ask the user if it's unclear which apply. This is repo-specific: e.g. reviewing a PR in this repo itself would mean `dev-essentials:general-conventions` and `dev-essentials:engineering-discipline`; a .NET backend repo would additionally mean `dotnet-backend-dev:dotnet-conventions`; another repo will have different (or no) registered convention skills.

## Phase 2 — Fetch PR metadata

Parse the PR URL to extract `<owner>`, `<repo>`, `<pullRequestNumber>` (`github-mcp-conventions` Rule 1 — never infer these from git remote or session context). Call:

```text
mcp__plugin_github_github__pull_request_read(
  method="get",
  owner="<owner>",
  repo="<repo>",
  pullRequestNumber=<number>)
```

Capture `headRefName`, `baseRefName`, `state`, `title`, `html_url`, `number`.

## Phase 3 — Get the diff locally

Never call `mcp__plugin_github_github__pull_request_read` with `method="get_diff"` for the review itself — follow `dev-essentials:review-loop`'s own `target=pr <id>` diff-resolution pattern instead of re-deriving it: after Phase 2's metadata, run `git fetch origin <headRefName> <baseRefName>`, then diff using the remote-tracking names: `git diff origin/<baseRefName>...origin/<headRefName>` — never rely on local branch names, which may be absent or stale.

For very large diffs, save to a temp file and read in chunks.

## Phase 4 — Evaluate against conventions

Apply the convention skill(s) invoked in Phase 1. Focus on real deviations, not stylistic preferences.

The category list below is **illustrative, not a checklist** — adapt it to whatever conventions the target repo's own skills actually define:

- **Domain models / types** — equality members, required-field validation, constructor validation. Compare to existing siblings in the same area of the repo.
- **Wrapper / value types** — factory methods, private constructors, comparers, whatever the repo's own wrapper convention specifies. Compare to an existing sibling wrapper.
- **Services** — DI pattern consistency with sibling services. **Watch for inconsistencies within the same class** — a new helper introduced but not propagated to the class's existing methods is a real finding, not a nitpick.
- **Converters / mappers** — extension-method or converter-class conventions, boundary-input validation.
- **Tests** — base-class conventions, AAA structure, assertion-library conventions, unit vs. integration categorization.
- **Documentation / Markdown** — this repo's own `dev-essentials:general-conventions` rules (e.g. frontmatter scalar quoting) when the diff touches skill/command/agent Markdown.
- **Exception / user-facing messages** — resource-based messages vs. inline string literals, if the repo centralizes user-facing strings.

Don't over-flag — see `dev-essentials:review-loop`'s finding-density guardrail (~1 Critical/High + 4 Medium + 3 Low/Nit per ~1,000 lines) for a sane ratio of findings to PR size.

## Phase 5 — Produce the HTML artifact

Output path: `Notes/Reviews/pr-<number>-review.html`.

Invoke `dev-essentials:create-html-artifact` (via the `Skill` tool) for the generic mechanics — self-contained inline CSS, the badge/annotation-chip/collapsible CSS component patterns, mermaid gotchas, and the section-by-section PR-review mapping, which lives in that skill's `references/recipes.md` Recipe 2 (PR / code-review artifact). End with the `ARTIFACT: <path>` line that skill's invocation contract requires. Reuse the most recent prior artifact in `Notes/Reviews/` as the visual template so the series stays visually consistent.

One PR-review-specific detail not covered by the recipe: the deep-link anchor convention. Every row in the findings table links via `<a href="#F-<anchor>">` to its file section, and that file section is anchored `id="F-<anchor>"`. Keep `<anchor>` stable (e.g. a slug of file path + line) so links survive artifact edits, and make sure every finding is linkable both ways (table → section, and back-references from the "major changes by file" collapsible sections).

# Orchestrator mode (`--orchestrate` flag)

For large PRs, delegate the context-heavy phases (2–4) to subagents instead of reading everything inline. Follow `dev-essentials:review-loop`'s "Large-target orchestrated mode" (`references/orchestrated-review.md`) — Role 1 (Target Explorer subagent, compact summary) → Role 2 (parallel, per-area Codebase/Convention Explorer subagents, structured findings only) → the density check between Role 2 and Role 3 → Role 3 (optional Finding Verifier subagent) → Role 4 (main-agent synthesis, reading back in only the specific lines the surviving findings anchor to). Invoke that reference directly rather than duplicating its subagent prompts here.

The one difference: the synthesis step doesn't feed a fixer. It feeds Phase 5 (the HTML artifact) and, optionally, Phase 6 (posting **new** findings as PR review comments).

# Phase 6 — Post findings as new PR review comments (only when explicitly requested)

Trigger on `--mode=post-all` / `--mode=post-<N>` / `--mode=post-<N>-<M>`. Default (`--mode=html-only`) stops after Phase 5.

## Before posting — check for existing duplicate threads

Fetch the PR's existing review threads first, using the same call `dev-essentials:process-pr-comments` uses for thread listing:

```text
mcp__plugin_github_github__pull_request_read(
  method="get_review_comments",
  owner="<owner>",
  repo="<repo>",
  pullRequestNumber=<number>,
  perPage=30)
```

Paginate to exhaustion with cursor-based `after` (`github-mcp-conventions` Rule 3 — this method uses `after`/`endCursor`, not page numbers). The response includes each thread's `isResolved`/`isOutdated` state, its comments, and each comment's `path`/`line`/`html_url`.

Compare each finding about to be posted against every existing thread — whoever authored it — using a simple heuristic: same `path`, an overlapping or near-adjacent line (within a few lines of the existing thread's anchor line, or an overlapping multi-line range), and a similar one-line gist. A clear match on all three is enough to call it a duplicate. Skip posting those, and note each one (with the existing thread's `html_url`) in the Output summary instead of silently dropping it.

## Post via the GitHub MCP review workflow

Per the GitHub MCP server's own documented review-comment workflow (create a pending review, add comments to it, then submit):

1. `mcp__plugin_github_github__pull_request_review_write(method="create", owner="<owner>", repo="<repo>", pullNumber=<number>)` — no `event` param, so this creates a **pending** review rather than submitting immediately.
2. `mcp__plugin_github_github__add_comment_to_pending_review(owner="<owner>", repo="<repo>", pullNumber=<number>, path="<file>", line=<N>, subjectType="LINE", body="<comment>")` for each finding anchored to a specific line. For a multi-line span, also pass `startLine=<first line>` with `side="RIGHT"` and `startSide="RIGHT"` (the new/right-hand version of the file — there is no separate offset to compute, unlike a start/end-offset PR-tracker API: this tool anchors by line number alone).
   - For findings that span multiple sites in a single file: anchor to the first violation and list the other sites in the body.
   - For findings that span multiple files: anchor to one representative first violation, list the others in the body, and cross-reference both files.
   - For cross-cutting/global concerns (e.g., a convention applied inconsistently across many files): **don't** call `add_comment_to_pending_review` for it — that tool requires a `path`. Instead fold the finding into the review's overall `body` text in step 3.
3. `mcp__plugin_github_github__pull_request_review_write(method="submit_pending", owner="<owner>", repo="<repo>", pullNumber=<number>, event="COMMENT", body="<summary + any cross-cutting findings from step 2>")` — submits the batch as one review with `COMMENT` (never `REQUEST_CHANGES` or `APPROVE`; this command reports, it doesn't gate merge).

If you need to discard a batch before submitting, use `method="delete_pending"` — there is no way to edit an individual pending comment once added.

## Tag taxonomy and comment shape

Use the tag taxonomy and per-tag semantics from `dev-essentials:process-pr-comments`'s `references/tag-actions.md` (`[ToFix]` / `[Optional]` / `[Suggestion]` / `[Question]` / `[ToDiscuss]` / `[Performance]` / `[OutOfScope]` / `[Note]` / `[PX]` / `[Repetition]`) — the same tags apply when posting a **new** finding, not only when replying to an existing one. Lead every comment with `**[Tag]**` in bold.

Severity → tag mapping (defaults; adjust per finding). Note that `[Performance]` is an ACTIONABLE tag in `tag-actions.md` with the same workflow as `[ToFix]` — never use it as an "info" label:

- Major / convention violation / real defect → `**[ToFix]**`
- Performance defect that genuinely warrants `tag-actions.md`'s `[Performance]` workflow (measurable regression, hot path, etc.) → `**[Performance]**`
- Minor cosmetic → `**[Optional]**`
- Minor refactor / test-coverage improvement → `**[Suggestion]**`
- Non-blocking performance observation (no measured impact, not a hot path) → `**[Suggestion]**`, `**[Note]**`, or `**[OutOfScope]**`, depending on how actionable it is — never `**[Performance]**`
- Info / operational follow-up → `**[OutOfScope]**` or `**[Note]**`

Comment shape:

```text
**[Tag]** <one-line summary>.

<diagnosis — what's wrong and why it matters>.

**Fix:** <concrete suggested fix>.
```

Markdown only — code-formatted symbols in backticks, no HTML tags.

## Before posting — verify

- `owner`/`repo` are present on every call (`github-mcp-conventions` Rule 2).
- The tag is the right one for this finding — comments cannot be edited or deleted after posting via MCP (`github-mcp-conventions` Rule 4); a wrong tag needs cleanup via the GitHub UI.
- The `line` (and `startLine`, if multi-line) actually points at the line you intend — re-derive from the source-branch file, e.g. `git show origin/<headRefName>:<path> | sed -n '<N>p'`, rather than trusting a line number computed earlier in the run.

# Phase 7 — Multi-PR mode (`--multi` mode)

If the input lists multiple PR URLs, dispatch one review subagent per PR via the `Agent` tool with `subagent_type: general-purpose`, `model: opus` (a per-PR critical review is judgment work, per the model matrix in the "Model selection" section of `dev-essentials:subagent-orchestration`), all dispatched in one message per that same skill's Rule 3 (agent dispatch has no foreground/background choice — issue every `Agent` call in a single message so they run concurrently) and Rule 5 (pure, unnamed one-shot dispatch — no `name`, no `team_name`). Each subagent gets:

- The PR URL.
- The path to the most recent reference artifact in `Notes/Reviews/` (so it can mirror the CSS/structure).
- The full Phase 1–5 instructions copied into the prompt (the subagent has no session context).
- An instruction to end with a single `ARTIFACT: <path>` line.
- **The `--orchestrate` flag, when the multi-PR invocation carried it** — stated explicitly in the prompt, so that subagent runs its own Phases 2–4 via its own sub-dispatches per **Orchestrator mode** rather than reading its whole diff inline. This fan-out is unconditional either way, so forwarding the flag is `--orchestrate`'s entire effect here — nothing about the top-level dispatch changes.

Each subagent reports back in under 200 words: what the PR does, finding counts by severity, the artifact path.

# Arguments

`$ARGUMENTS` takes one of two top-level shapes:

- `<pr-url> [--mode=<mode>] [--orchestrate]` — single-PR review. `<pr-url>` is the first positional argument.
- `--multi <url1> <url2> ... [--orchestrate]` — multi-PR review (Phase 7). The `--multi` flag replaces `<pr-url>` as the first argument and consumes the space-separated URL list that follows it; there is no separate leading single-PR URL in this shape.

The `--orchestrate` flag can appear in any position after the URL (single-PR shape) or after the last `--multi` URL (multi-PR shape), and combines with any mode.

Modes (single-PR shape only):

- `<pr-url>` alone → produce the HTML artifact only (Phases 1–5).
- `<pr-url> --mode=html-only` → same as above (explicit).
- `<pr-url> --mode=post-all` → produce the artifact, then post every finding as a PR review comment.
- `<pr-url> --mode=post-<N>` → post only finding number `N` (1-based, matching the artifact's findings table).
- `<pr-url> --mode=post-<N>-<M>` → post findings `N` through `M`.

Multi-PR shape:

- `--multi <url1> <url2> ...` → dispatch parallel review subagents (Phase 7). `--orchestrate` in this shape is forwarded into every per-PR subagent, which then runs its own Phases 2–4 via Orchestrator mode.

`--orchestrate` combines with any mode. **In the single-PR shape** (e.g. `<pr-url> --mode=post-all --orchestrate`): Phases 1, 5, and 6 stay inline, Phases 2–4 go to subagents per Orchestrator mode above. **In the multi-PR shape**: it is forwarded per Phase 7, and each per-PR subagent then applies that same single-PR rule to its own PR. See **Mode selection** for when it's worth it.

# Output

End the response with the `ARTIFACT: <path>` line — nothing else on that
line, per `create-html-artifact`'s output contract — followed by a
separate findings-summary line, per PR:

```text
ARTIFACT: Notes/Reviews/pr-<number>-review.html
N findings (X critical · Y major · Z minor · W info)
```

If comments were posted, also list each posted comment's `html_url` and its anchor (`<path>:<line>`), and any findings skipped as duplicates of an existing thread (with the existing thread's `html_url`).
