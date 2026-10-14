---
name: github-mcp-conventions
description: "Conventions for calling GitHub MCP tools (`mcp__plugin_github_github__*`) for PR and issue work. Covers the never-infer-owner/repo rule (always pass user-supplied values verbatim) and the rule to pass `owner` and `repo` on every GitHub MCP call. Also covers pagination discipline (bounded page size, stop on a partial page), and no comment edit or comment delete through MCP. Also covers the no-REST-fallback rule (ask the user to reconnect with /mcp, never fall back to the gh CLI or curl). Apply whenever GitHub MCP tools are used for PR review, issue management, or repository operations. Examples: read PRs, post review comments, create issues, list branches, or fetch file contents. Triggers on any session that calls `mcp__plugin_github_github__*` tools."
---

# GitHub MCP Conventions

Apply these rules to every GitHub MCP call. In a multi-stage workflow, delegate high-volume GitHub MCP reads to subagents, so that the context of the main agent stays clean (`dev-essentials:subagent-orchestration` Rule 4).

## Rule 1 — Never substitute or infer the repo identifier

Pass the `owner` and `repo` that the user supplied **verbatim** to every GitHub MCP call. Do not derive them from PR metadata, a remote URL, fork relationships, or the session context.

**Why:** a session can have several repos in view, for example the upstream repo and a fork, or two sibling services. Suppose that you read `head.repo.full_name` from PR metadata and use it instead of `base.repo.full_name`. Then the call can target the fork instead of the upstream repo, and post comments or create issues in the wrong place.

**How to apply**:

- If the user says "review PR #42 in `octo-org/octo-repo`", pass `owner: "octo-org"` and `repo: "octo-repo"`. Do not infer them from any metadata.
- If the user gives only a URL (for example `https://github.com/<owner>/<repo>/pull/<id>`), parse `owner` and `repo` from the URL path. Pass them exactly as parsed.
- If `owner` or `repo` is ambiguous (not supplied and not parseable from a URL), **ask the user** before you make any call.
- One exception: without `--interactive`, a workflow that documents it can take `owner/repo` from the `origin` remote of the repository under work. It must report that value as taken from the remote. With `--interactive`, this rule holds as written.

**Anti-patterns**:

- "The `head.repo.owner.login` field of the PR says `<fork-owner>`, so I use that as `owner`." No. Use the value that the user supplied, or the owner of the base repo.
- "I infer the repo from the remote URL of the current git working tree." No. Ask the user explicitly, unless the documented exception above applies.
- "I already called `pull_request_read` and got the repo name from the response. I use that for the next call." Use that value only after you make sure that it matches the `owner/repo` that the user supplied. If it does not match, ask.

## Rule 2 — Always pass `owner` and `repo` on every GitHub MCP call

Pass `owner` and `repo` on every GitHub MCP tool call. The rule applies to every `mcp__plugin_github_github__*` tool. No default comes from the session, and the server does not supply one. If `owner` or `repo` is missing from a call that you are about to make, stop and add it.

**How to apply**:

- Before each GitHub MCP call, make sure that `owner` and `repo` are in the call payload.
- In a loop, for example a loop over comment pages, pass `owner` and `repo` on every iteration. They do not persist between calls.

## Rule 3 — Pagination: bounded `perPage`, stop on partial page

If a GitHub MCP tool returns paginated results, always paginate to the end with these rules:

1. Pass the page size (`perPage` in the tool schemas) explicitly on every paginated call. Typical values: `30` for comment or thread lists, and `100` for list operations that return many results.
2. Use `page` (starts at 1), a cursor, or `since`, as the tool supports. For a cursor method, pass the `endCursor` of the previous page as `after`. Example: `pull_request_read` with `method: "get_review_comments"`.
3. **Stop condition:** a page with fewer items than the page size is the last page. Stop, and do not request the next page. For a cursor method, the response field `pageInfo.hasNextPage` set to `false` also marks the last page.
4. **Never stop early** on the first non-empty page. Large PRs have many comments, and large repos have many branches. A stop after the first page drops data silently.

**Example: paginating PR comments**

```
page=1, perPage=30 → 30 comments → continue
page=2, perPage=30 → 30 comments → continue
page=3, perPage=30 → 17 comments → stop (17 < 30, last page)
```

**Anti-patterns**:

- One call to a list tool without a page size, with the result treated as complete.
- A stop at a page that is not empty but smaller than expected, without a comparison against the page size.
- An unbounded page size (for example 1000) to avoid pagination. The server caps the page size, so the result is still paginated.

## Rule 4 — No comment-edit or comment-delete via MCP

Do not edit or delete a posted comment through MCP. For PR review comments, the GitHub MCP plugin has no edit or delete tool. Clean up a posted comment in the GitHub web UI (PR → Conversation → the three-dot menu of the comment).

**Why this matters:** a stub or test comment can land on a real PR thread, for example during a failed post. MCP cannot undo it. The only repair path is the GitHub web UI.

**How to apply**:

- Before you post any review comment, make sure that `owner`, `repo`, `pullNumber`, and `commentId` (for replies) are correct. Rules 1 and 2 apply. Do not send test calls against real PRs.
- If a post fails, call `pull_request_read` to find out whether the comment landed before you retry. The MCP layer can return an error even after a successful post, and a blind retry posts a duplicate.
- If a stub comment does land, note it explicitly in chat: "A stub comment landed on PR #`<id>` — please delete it via the GitHub UI (PR → Conversation → the comment → Delete)."
- Do not try to "overwrite" a stub with a corrected comment. That adds a second comment next to the stub and doubles the clutter.

**Pending review batches:** a batch from `add_comment_to_pending_review` is not visible until `pull_request_review_write` submits it. Do not discard a pending batch through MCP. Dismiss it in the GitHub UI.

## Rule 5 — No REST/`gh`-CLI fallback when MCP is unavailable

If GitHub MCP tools are missing or misbehave, never use `gh pr comment`, `curl`, direct REST calls, or any script to work with GitHub instead.

**Why:** the GitHub MCP server is the sanctioned interface. REST workarounds bypass the consistent tool surface, need credential management, and are explicitly prohibited. If the MCP server is unavailable, the correct repair is to reconnect it, not to work around it.

**How to apply**:

- If the session has no `mcp__plugin_github_github__*` tools, ask the user to reconnect with `/mcp`, and wait.
- If a tool returns an unexpected error, diagnose the call. The usual causes are a missing `owner` or `repo`, a wrong type for `pullNumber`, or a permissions gap. Do not use the `gh` CLI or `curl` as a fallback.
- `dev-essentials:subagent-orchestration` Rule 4 has the same rule for subagents. If MCP is missing in a subagent, the subagent reports the error upward and does not fall back to REST either.
- One named exception: Phase 9c.4 step 7 of `dev-essentials:audit-personal-conventions` creates a PR with `gh pr create`. If the session has no GitHub MCP tools, the step uses `gh`. The step also uses `gh` after an MCP call fails with a connection error or an authentication error. The exception covers only that step. It does not cover an MCP call that fails because of a wrong parameter.

**Anti-patterns**:

- "MCP returned an error, so I post with `gh pr comment` directly." No. Fix the MCP call.
- "The MCP tool does not work, so I write a shell script with `curl` and the GitHub REST API." No. Ask the user to fix `/mcp`.
- "Just a quick `gh pr view`, because MCP is slow." No. A slow MCP call is never a reason to use `gh`.

## Rule 6 — After a create call echoes a relationship, re-read to confirm it landed

A create call can report that it also set up a relationship: `issue_write` with a `parent_issue_number`, or `sub_issue_write`. Do not trust the echoed response as proof that the link exists. Read the relationship again from its authoritative endpoint before you report it as set up.

**Why:** the `parent_issue_number` that the create call echoes, and the `parent` and `sub_issues_summary` fields of an `issue_read` `method: "get"` response, are best-effort summaries. The tool can omit them or return stale values. A parent attach in the same call can fail silently. The new issue then has no parent, but the create response still shows the requested number. A report of a link that did not land is worse than no report.

**How to apply**:

- After `issue_write` or `sub_issue_write` (or any create call whose response echoes a parent or child link), call `issue_read` with `method: "get_parent"` on the new issue. Make sure that it returns the expected parent.
- If `get_parent` returns no parent or a different one, the attach did not land. Set up the link explicitly with `sub_issue_write` (`method: "add"`). Then read it again with `get_parent`. Do not report the link before a `get_parent` read shows it.
- The `mode: create` workflow of `dev-essentials:task-composer` already works this way. Treat it as the standard for every GitHub MCP call that creates a relationship, not as a rule of that agent only.

**Anti-patterns**:

- "`issue_write` returned `parent_issue_number: 42`, so the sub-issue link exists." No. Read it with `get_parent`.
- "The `get` response has a `parent` field, and that is my proof." No. `parent` and `sub_issues_summary` are best-effort and optional. Use `get_parent`.

## Rule 7 — Read a PR's diff from local git, not a token-heavy MCP diff call

For anything beyond a small change, do not get the diff of a PR through `pull_request_read` with `method: "get_diff"` or `method: "get_files"`. Read it from local git instead.

**Why:** a large diff response fills the context. If it exceeds the tool-output limit, Claude Code saves it to a side file, and you pay tokens again to read it back. Local git costs less, and you can limit the read to the paths that you need.

**How to apply (use local git instead)**:

Read the base branch name of the PR from `pull_request_read` `method: "get"` (`base.ref`, a plain branch name without a `refs/heads/` prefix). Fetch the head of the PR from the `pull/<id>/head` ref, not by the name of the head branch. For a PR from a fork, the head branch is not on `origin`, but `pull/<id>/head` is. Then run:

```bash
git fetch origin <base> "+refs/pull/<id>/head:refs/remotes/origin/pull/<id>/head"
git diff --stat origin/<base>...origin/pull/<id>/head
git diff origin/<base>...origin/pull/<id>/head -- <path>   # targeted reads
git log --oneline origin/<base>..origin/pull/<id>/head
```

This recipe needs `origin` to be the base repository of the PR. If the fetch fails, stop and ask the user which remote holds the base repository. Then use that remote in place of `origin`. Do not fall back to the name of the head branch.

This is not a new pattern. The `target=pr <id>` resolution of `dev-essentials:review-loop` already fetches and diffs this way. Treat it as the precedent, and do not invent a new way at each call site.

## Thread anchors and `html_url`

To reference a PR comment in chat output or in a reply, use the `html_url` field of the comment from `pull_request_read`. It is the stable browser URL of the thread. Format: `https://github.com/<owner>/<repo>/pull/<id>#discussion_r<comment-id>`.

Do not build thread URLs by hand from `pullNumber` and `commentId`. The `#discussion_r<id>` fragment format is an implementation detail that can change. Always use the `html_url` that the API returns.
