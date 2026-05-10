---
name: github-mcp-conventions
description: "Conventions for calling GitHub MCP tools (`mcp__plugin_github_github__*`) for PR and issue work. Covers the never-infer-owner/repo rule (always pass user-supplied values verbatim), the always-pass-owner-and-repo rule on every GitHub MCP call, pagination discipline (bounded per_page, stop on partial page), no comment-edit or comment-delete via MCP (clean up via GitHub UI), and the no-REST-fallback rule (ask user to reconnect via /mcp, never fall back to gh CLI or curl). Apply whenever GitHub MCP tools are used: reading PRs, posting review comments, creating issues, listing branches, fetching file contents. Triggers on any session that calls `mcp__plugin_github_github__*` tools for PR review, issue management, or repository operations."
---

# GitHub MCP Conventions

These rules encode hard-won gotchas when calling the GitHub MCP plugin. Every rule has a real failure mode behind it; apply them defensively on every GitHub MCP call.

For GitHub MCP work that is part of a multi-stage workflow, see `dev-essentials:subagent-orchestration` Rule 4 — delegate high-volume MCP reads to subagents so main-agent context stays clean.

## Rule 1 — Never substitute or infer the repo identifier

Pass the user-supplied `owner` and `repo` **verbatim** to every GitHub MCP call. Do not derive them from PR metadata, remote URL, fork relationships, or session context.

**Why:** A session may have multiple repos in view (the upstream repo and a fork, or two sibling services). Silently inferring `owner/repo` from PR metadata — e.g., reading `head.repo.full_name` and using that instead of `base.repo.full_name` — can silently target the fork instead of the upstream, posting comments or creating issues in the wrong place.

**How to apply:**

- When the user says "review PR #42 in `Vasar007/vasar-plugins-marketplace`", pass `owner: "Vasar007"`, `repo: "vasar-plugins-marketplace"` — do not infer from any metadata.
- If the user provides only a URL (e.g., `https://github.com/<owner>/<repo>/pull/<id>`), parse `owner` and `repo` from the URL path. Pass them exactly as parsed.
- If the `owner` or `repo` is ambiguous (not supplied and not parseable from a URL), **ask the user** before making any call.

**Anti-patterns:**

- "The PR's `head.repo.owner.login` field says `<fork-owner>`, so I'll use that as `owner`" — no. Use the user-supplied value or the base repo owner.
- "I'll infer the repo from the remote URL of the current git working tree" — no. Ask the user explicitly.
- "I already called `pull_request_read` and got the repo name from the response — I'll use that for the next call" — only if that value matches the user-supplied `owner/repo`. If it doesn't, ask.

## Rule 2 — Always pass `owner` and `repo` on every GitHub MCP call

Passing `owner` and `repo` is required on every GitHub MCP tool call. There are no session-inferred defaults.

**Affected tools** (non-exhaustive; the rule applies to all `mcp__plugin_github_github__*` tools):

| Tool | Required fields |
|---|---|
| `pull_request_read` | `owner`, `repo`, `pullRequestNumber` |
| `list_pull_requests` | `owner`, `repo` |
| `add_comment_to_pending_review` | `owner`, `repo`, `pullRequestNumber` |
| `add_reply_to_pull_request_comment` | `owner`, `repo`, `pullRequestNumber`, `commentId` |
| `pull_request_review_write` | `owner`, `repo`, `pullRequestNumber` |
| `issue_read` | `owner`, `repo`, `issueNumber` |
| `issue_write` | `owner`, `repo` |
| `create_pull_request` | `owner`, `repo` |
| `list_branches` | `owner`, `repo` |
| `get_file_contents` | `owner`, `repo`, `path` |

If any required field is absent from a call you are about to make, stop and fill it in. Do not rely on the server to supply a default — it won't.

**How to apply:**

- Before each GitHub MCP call, confirm `owner` and `repo` are present in your call payload.
- If you are in a loop (e.g., paginating comments), pass `owner` and `repo` on every iteration — do not assume they persist between calls.

## Rule 3 — Pagination: bounded `per_page`, stop on partial page

When a GitHub MCP tool returns paginated results, always paginate to exhaustion using these rules:

1. Pass `per_page` explicitly on every paginated call. Typical values: `30` for comment/thread lists, `100` for list operations where you expect many results.
2. Use `page` (1-indexed) or `cursor` / `since` depending on what the tool supports.
3. **Stop condition:** a page that returns fewer items than `per_page` is the last page. Stop — do not request the next page.
4. **Never stop early** on the first non-empty page. Large PRs have many comments; large repos have many branches. Stopping after the first page silently drops data.

**Example — paginating PR comments:**

```
page=1, per_page=30 → 30 comments → continue
page=2, per_page=30 → 30 comments → continue
page=3, per_page=30 → 17 comments → stop (17 < 30, last page)
```

**Anti-patterns:**

- Calling a list tool once without `per_page` and treating the result as complete.
- Stopping when a page is non-empty but smaller than expected without checking against `per_page`.
- Using an unbounded `per_page` (e.g., 1000) to avoid pagination — the server caps the page size and the result is still paginated.

## Rule 4 — No comment-edit or comment-delete via MCP

The GitHub MCP plugin does not expose tools to edit or delete existing PR review comments. Once a review comment is posted, it cannot be modified or removed through MCP — it must be cleaned up via the GitHub web UI (PR → Conversation → the comment's three-dot menu).

**Why this matters:** If a stub or test comment lands on a real PR thread (e.g., during a failed posting attempt), that comment cannot be undone via MCP. The only repair path is the GitHub web UI.

**How to apply:**

- Before posting any review comment, verify `owner`, `repo`, `pullRequestNumber`, and `commentId` (for replies) are correct (Rule 1 + Rule 2). Do not fire test calls against real PRs.
- If posting fails, call `pull_request_read` to check whether the comment actually landed before retrying. The MCP layer may return an error even when the comment posted successfully — a blind retry posts a duplicate.
- If a stub comment does land, note it explicitly in chat: "A stub comment landed on PR #`<id>` — please delete it via the GitHub UI (PR → Conversation → the comment → Delete)."
- Do not attempt to "overwrite" a stub by posting a corrected comment; it adds a second comment alongside the stub, compounding the clutter.

**Pending review batches:** When using `add_comment_to_pending_review`, the batch is not visible until `pull_request_review_write` submits it. If you need to discard a pending batch, dismiss it via the GitHub UI — there is no MCP tool to cancel a pending review.

## Rule 5 — No REST/`gh`-CLI fallback when MCP is unavailable

Never substitute `gh pr comment`, `curl`, direct REST calls, or any scripting approach to interact with GitHub when MCP tools are missing or misbehaving.

**Why:** The GitHub MCP server is the sanctioned abstraction. REST workarounds bypass the consistent tool surface, require credential management, and have been explicitly prohibited. If the MCP server is unavailable, the correct repair is to reconnect it — not to work around it.

**How to apply:**

- If GitHub MCP tools are not visible in the session (`mcp__plugin_github_github__*` tools absent from tool list), ask the user to reconnect via `/mcp` and wait.
- If a specific tool returns an unexpected error, diagnose the call (usually missing `owner`/`repo`, wrong `pullRequestNumber` type, or a permissions gap) — do not reach for `gh` CLI or `curl` as a fallback.
- See also `dev-essentials:subagent-orchestration` Rule 4: if MCP is missing in a subagent, surface the error upward; do not silently fall back to REST in the subagent either.

**Anti-patterns:**

- "MCP returned an error, let me use `gh pr comment` to post directly" — no. Fix the MCP call.
- "I'll write a shell script using `curl` and the GitHub REST API since the MCP tool isn't working" — no. Ask the user to fix `/mcp`.
- "Just a quick `gh pr view` since the MCP is slow" — no exceptions.

## Tool reference table

Quick map of the most common GitHub MCP tools and their primary use:

| Tool | Use |
|---|---|
| `pull_request_read` | Read PR metadata + review comments (paginated via `pull_request_read` with review state). |
| `list_pull_requests` | List PRs in a repo (filter by state: `open`, `closed`, `all`). |
| `add_comment_to_pending_review` | Add a line comment to a pending (draft) review batch. |
| `add_reply_to_pull_request_comment` | Reply to an existing review thread by `commentId`. |
| `pull_request_review_write` | Submit or dismiss a pending review batch; create a simple PR comment. |
| `issue_read` | Read a single issue by `issueNumber`. |
| `issue_write` | Create or update an issue (pass `issueNumber` to update). |
| `create_pull_request` | Open a new PR from `head` to `base`. |
| `list_branches` | List branches in a repo (paginated). |
| `get_file_contents` | Read a file from the repo at a given `ref` (branch, tag, or commit SHA). |

All tools require `owner` and `repo` on every call (Rule 2). Paginate any list tool per Rule 3.

## Thread anchors and `html_url`

When referencing a specific PR comment in chat output or in a reply, use the comment's `html_url` field (returned by `pull_request_read`) — this is the stable browser-navigable URL for the thread. Format: `https://github.com/<owner>/<repo>/pull/<id>#discussion_r<comment-id>`.

Do not reconstruct thread URLs manually from `pullRequestNumber` and `commentId` alone — the `#discussion_r<id>` fragment format is an implementation detail that could change. Always use the `html_url` returned by the API.
