---
description: "Review a GitHub PR and report on it, with no code edits: evaluate the diff against the repo conventions, render an HTML review artifact, and optionally post the findings as PR review comments."
argument-hint: "<pr-url> [--mode=html-only|post-all|post-<N>|post-<N>-<M>] [--orchestrate] | --multi <url1> <url2> ... [--orchestrate]"
---

Review the GitHub pull request: $ARGUMENTS

# Not a duplicate of `dev-essentials:review-loop`

`review-loop` also supports `target=pr <id>` end-to-end. It ends with a verify-then-fix pass that **edits code**. Use it for the goal "review and fix".

This command is for the other goal, "review and report". It evaluates a PR against the conventions, makes an HTML artifact to share, and optionally posts the findings back as new PR review comments. It never edits the reviewed code, in any mode.

# Mode selection

Look in `$ARGUMENTS` for the `--orchestrate` flag (anywhere after the URL):

- **Without `--orchestrate`** (default, the "inline" mode): the main agent reads everything itself. This mode fits small PRs (under about 1,500 lines), where the full diff fits in the context.
- **With `--orchestrate`** (the delegation mode): the main agent dispatches subagents for the steps that need much context. These steps are PR exploration, the reading of the codebase and the diff, and convention evaluation. The main agent keeps only the synthesized findings and **the specific lines that those findings point to**. This mode fits large PRs (over about 2,000 lines or over 30 files) and PRs that touch many separate areas. It also fits a run where the user wants to keep the main context for follow-up work.

With `--orchestrate`, follow the section **Orchestrator mode** below instead of Phases 2 to 4. Phase 1 (setup), Phase 5 (HTML artifact), and Phase 6 (post comments) are the same in both modes. Phase 7 (multi-PR) is different: it always dispatches one review subagent for each PR, **with or without `--orchestrate`**. So the flag has no effect at the top level there. Phase 7 passes it on to each subagent. See Phase 7.

# Workflow

## Phase 1 — Setup

Invoke `dev-essentials:github-mcp-conventions` with the `Skill` tool. All its rules apply here. These rules matter most for this workflow:

- Rule 1: never infer `owner` or `repo`. Pass the values of the user word for word.
- Rule 2: pass `owner` and `repo` on every call.
- Rule 3: pagination.
- Rule 4: no comment edit or comment delete after a post. Clean up in the GitHub UI.
- Rule 5: no fallback to REST or to the `gh` CLI.

Then invoke the convention skills that apply to the **target repo**. Find them in the `CLAUDE.md` of that repo. If it is not clear which skills apply, ask the user. The skills differ for each repo. For example, a PR in a plugin marketplace of Markdown skills needs `dev-essentials:general-conventions` and `dev-essentials:engineering-discipline`. A .NET backend repo also needs `dotnet-backend-dev:dotnet-conventions`. Another repo can have other registered convention skills, or none.

## Phase 2 — Fetch PR metadata

Parse the PR URL for `<owner>`, `<repo>`, and `<number>`. Never infer these values from the git remote or from the session context (`github-mcp-conventions` Rule 1). Call:

```text
mcp__plugin_github_github__pull_request_read(
  method="get",
  owner="<owner>",
  repo="<repo>",
  pullNumber=<number>)
```

From the response, keep `title`, `state`, `html_url`, and `number`. Also keep the base branch as `<baseRefName>` (from `base.ref`).

## Phase 3 — Get the diff locally

Never call `mcp__plugin_github_github__pull_request_read` with `method="get_diff"` for the review itself (`github-mcp-conventions` Rule 7). Use the `target=pr <id>` diff steps of `dev-essentials:review-loop`, and do not invent other steps. After Phase 2, run `git fetch origin <baseRefName> "+refs/pull/<number>/head:refs/remotes/origin/pull/<number>/head"`. The `pull/<number>/head` ref also exists for a PR from a fork, whose head branch is not on `origin`. If the fetch fails, stop and ask the user which remote holds the base repository. Then diff with the remote-tracking names: `git diff origin/<baseRefName>...origin/pull/<number>/head`. Never use local branch names, because they can be missing or stale.

Run this diff once for the production paths and once for the test paths, so that you read them separately. Put `-- <paths>` at the end of each command. If a diff is very large, save it to a temp file and read it in parts.

## Phase 4 — Evaluate against conventions

Apply the convention skills of Phase 1. Compare the diff with the conventions. Report a style preference as a minor finding. To find a sibling for a comparison in a large repo, you can dispatch the agent type `dev-essentials:code-locator`. It returns locations only, and you make the comparison.

The categories below are **examples, not a full list**. Adapt them to the conventions that the skills of the target repo define:

- **Domain models and types**: equality members, validation of required fields, and constructor validation. Compare with existing siblings in the same area of the repo.
- **Wrapper and value types**: factory methods, private constructors, comparers, and the other parts that the wrapper convention of the repo asks for. Compare with an existing sibling wrapper.
- **Services**: the DI pattern matches the sibling services. **Look for inconsistencies inside one class**. A new helper that the existing methods of the class do not use is a real finding, not a nitpick.
- **Converters and mappers**: the conventions for extension methods or converter classes, and the validation of boundary input.
- **Tests**: base-class conventions, AAA structure, assertion-library conventions, and the split between unit and integration tests.
- **Documentation and Markdown**: for a diff that changes skill, command, or agent Markdown, the rules of `dev-essentials:write-markdown`, for example the quoting of frontmatter scalars.
- **Exception and user-facing messages**: if the repo keeps its user-facing strings in one place, messages come from resources, not from inline string literals.

Report every finding with a severity. Sort the findings table of the artifact by severity, so that the reader and `--mode=post-<N>-<M>` start with the most severe ones.

## Phase 5 — Produce the HTML artifact

The notes folder is `${user_config.notes_dir}`. If that value still shows as a `${...}` placeholder, no value is saved, and the notes folder is `Notes`. The reviews folder is `Reviews/` in the notes folder.

Output path: `pr-<number>-review.html` in the reviews folder.

Invoke `dev-essentials:create-html-artifact` with the `Skill` tool. Map the review onto the sections of Recipe 2 (PR / code-review artifact) in its `references/recipes.md`. Give the `ARTIFACT: <path>` line that the invocation contract of that skill requires (see Output). Use the most recent prior artifact in the reviews folder as the visual template, so that the series looks the same.

Recipe 2 links each row of the findings table (`<a href="#F-<anchor>">`) to the file section with `id="F-<anchor>"`. Keep each `<anchor>` stable, so that the links still work after edits of the artifact. An example is a slug of the file path and the line. Make sure that each finding has links in both directions: from the table to the section, and back from the collapsible sections "major changes by file".

# Orchestrator mode (`--orchestrate` flag)

For a large PR, delegate the phases that need much context (2 to 4) to subagents, and do not read everything inline. Follow the "Large-target orchestrated mode" of `dev-essentials:review-loop` (`references/orchestrated-review.md`):

1. Role 1: a Target Explorer subagent builds a fact map of the PR, with no judgment.
2. The map comparison between Role 1 and Role 2.
3. Role 2: parallel Area Explorer subagents, one for each area, read the code and the diff against the conventions. They return structured findings only.
4. The collation between Role 2 and Role 3.
5. Role 3: the main agent reads back only the specific lines that the findings point to, makes sure that each diagnosis matches them, and writes the synthesis.

Read that reference file directly. This command does not copy its subagent prompts.

The one difference: the synthesis does not feed a fixer. It feeds Phase 5 (the HTML artifact). If `--mode` asks for posts, it also feeds Phase 6 (the post of **new** findings as PR review comments).

# Phase 6 — Post findings as new PR review comments (only when explicitly requested)

This phase runs only with `--mode=post-all`, `--mode=post-<N>`, or `--mode=post-<N>-<M>`. The default (`--mode=html-only`) stops after Phase 5.

## Before posting — check for existing duplicate threads

First fetch the existing review threads of the PR. Use the same call that `dev-essentials:process-pr-comments` uses to list threads:

```text
mcp__plugin_github_github__pull_request_read(
  method="get_review_comments",
  owner="<owner>",
  repo="<repo>",
  pullNumber=<number>,
  perPage=30)
```

Read all pages, and pass the `endCursor` of the previous page as `after` (`github-mcp-conventions` Rule 3). This method uses a cursor, not page numbers. The response has the `is_resolved` and `is_outdated` state of each thread, its comments, and the `path`, `line`, and `html_url` of each comment.

Compare each finding that you plan to post with each existing thread, whoever wrote it. Use a simple test with three parts:

1. The same `path`.
2. A line that overlaps the anchor line of the thread or is near it (within a few lines), or a range of lines that overlaps.
3. A similar one-line gist.

A clear match on all three parts makes the finding a duplicate. Do not post a duplicate. List each one in the Output summary, with the `html_url` of the existing thread, and do not drop it in silence.

## Post via the GitHub MCP review workflow

Follow the review-comment workflow that the GitHub MCP server documents: create a pending review, add comments to it, then submit it.

1. `mcp__plugin_github_github__pull_request_review_write(method="create", owner="<owner>", repo="<repo>", pullNumber=<number>)`. The call has no `event` parameter, so it creates a **pending** review and does not submit it.
2. `mcp__plugin_github_github__add_comment_to_pending_review(owner="<owner>", repo="<repo>", pullNumber=<number>, path="<file>", line=<N>, subjectType="LINE", body="<comment>")` for each finding on a specific line. For a span of several lines, also pass `startLine=<first line>`, `side="RIGHT"`, and `startSide="RIGHT"` (the new, right-hand version of the file). The tool anchors by line number only, so you do not compute an offset.
   - A finding with several sites in one file: anchor it to the first violation, and list the other sites in the body.
   - A finding with sites in several files: anchor it to one typical first violation, list the other sites in the body, and refer to both files.
   - A cross-cutting or global concern, for example a convention that many files apply in different ways: **do not** call `add_comment_to_pending_review` for it, because that tool requires a `path`. Put the finding into the overall `body` of the review in step 3.
3. `mcp__plugin_github_github__pull_request_review_write(method="submit_pending", owner="<owner>", repo="<repo>", pullNumber=<number>, event="COMMENT", body="<summary + any cross-cutting findings from step 2>")`. This call submits the batch as one review with `COMMENT`. Never use `REQUEST_CHANGES` or `APPROVE`, because this command reports and does not gate the merge.

To discard a batch before you submit it, use `method="delete_pending"`. You cannot edit a single pending comment after you add it.

## Tag taxonomy and comment shape

Use the tags and their meanings from `references/tag-actions.md` of `dev-essentials:process-pr-comments`: `[ToFix]`, `[Optional]`, `[Suggestion]`, `[Question]`, `[ToDiscuss]`, `[Performance]`, `[OutOfScope]`, `[Note]`, `[PX]`, and `[Repetition]`. The same tags apply to a **new** finding, not only to a reply to an existing thread. Start every comment with `**[Tag]**` in bold.

Map severity to a tag with these defaults, and adapt them for each finding. In `tag-actions.md`, `[Performance]` is an ACTIONABLE tag with the same workflow as `[ToFix]`. Never use it as an info label.

- Major, convention violation, or real defect → `**[ToFix]**`
- Performance defect that needs the `[Performance]` workflow of `tag-actions.md` (a measurable regression, a hot path, or a similar case) → `**[Performance]**`
- Minor cosmetic issue → `**[Optional]**`
- Minor refactor or better test coverage → `**[Suggestion]**`
- Non-blocking performance observation (no measured impact, not a hot path) → `**[Suggestion]**`, `**[Note]**`, or `**[OutOfScope]**`. Pick by how actionable it is. Never `**[Performance]**`.
- Info or operational follow-up → `**[OutOfScope]**` or `**[Note]**`

Comment shape:

```text
**[Tag]** <one-line summary>.

<diagnosis — what's wrong and why it matters>.

**Fix:** <concrete suggested fix>.
```

Use Markdown only: symbols as code in backticks, and no HTML tags.

## Before posting — verify

- Make sure that `owner` and `repo` are present on every call (`github-mcp-conventions` Rule 2).
- Make sure that the tag fits the finding. After the post, you cannot edit or delete the comment through MCP (`github-mcp-conventions` Rule 4). A wrong tag then needs a cleanup in the GitHub UI.
- Make sure that the `line` (and `startLine` for a span of several lines) points at the line that you mean. Read the line again from the file of the source branch, for example with `git show origin/pull/<number>/head:<path> | sed -n '<N>p'`. Do not trust a line number from earlier in the run.

# Phase 7 — Multi-PR mode (`--multi` mode)

If the input lists several PR URLs, dispatch one review subagent for each PR with the `Agent` tool: `subagent_type: general-purpose` and `model: opus`. A critical review of a PR is judgment work (see the model matrix in the section "Model selection" of `dev-essentials:subagent-orchestration`). Put every `Agent` call into one message, so that the subagents run at the same time (Rule 3 of that skill). Each dispatch is a pure, unnamed one-shot dispatch, with no `name` and no `team_name` (Rule 5 of that skill). Each subagent gets:

- The PR URL.
- The path of the most recent reference artifact in the reviews folder, so that it can copy the CSS and the structure.
- The full instructions of Phases 1 to 5, copied into the prompt, because the subagent has no session context.
- An instruction to end with one `ARTIFACT: <path>` line.
- **The `--orchestrate` flag**. If the multi-PR invocation has the flag, state it explicitly in the prompt. The subagent then runs its own Phases 2 to 4 through its own dispatches (see **Orchestrator mode**). It does not read its whole diff inline. The fan-out happens with or without the flag, so this forwarding is the only effect of `--orchestrate` here. The dispatch at the top level does not change.

Each subagent reports back in under 200 words: what the PR does, the finding counts by severity, and the artifact path.

# Arguments

`$ARGUMENTS` has one of two top-level shapes:

- `<pr-url> [--mode=<mode>] [--orchestrate]`: a review of one PR. `<pr-url>` is the first positional argument.
- `--multi <url1> <url2> ... [--orchestrate]`: a review of several PRs (Phase 7). `--multi` takes the place of `<pr-url>` as the first argument. It takes the list of URLs after it, separated by spaces. This shape has no separate single-PR URL at the start.

The `--orchestrate` flag can come at any position after the URL (single-PR shape), or after the last `--multi` URL (multi-PR shape). It works with any mode.

Modes (single-PR shape only):

- `<pr-url>` alone → only the HTML artifact (Phases 1 to 5).
- `<pr-url> --mode=html-only` → the same, stated explicitly.
- `<pr-url> --mode=post-all` → the artifact, then a PR review comment for every finding.
- `<pr-url> --mode=post-<N>` → a post of finding number `N` only (1-based, as in the findings table of the artifact).
- `<pr-url> --mode=post-<N>-<M>` → a post of findings `N` to `M`.

Multi-PR shape:

- `--multi <url1> <url2> ...` → parallel review subagents (Phase 7).

`--orchestrate` in the single-PR shape (for example `<pr-url> --mode=post-all --orchestrate`): Phases 1, 5, and 6 stay inline, and Phases 2 to 4 go to subagents, as **Orchestrator mode** says. In the multi-PR shape, Phase 7 passes the flag on, and each subagent applies the single-PR rule to its own PR. See **Mode selection** for the PR sizes where the flag helps.

# Output

In the final response, give the `ARTIFACT: <path>` line for each PR, with nothing else on that line (the output contract of `create-html-artifact`). Put a separate line with the finding counts after it:

```text
ARTIFACT: <reviews-folder>/pr-<number>-review.html
N findings (X critical · Y major · Z minor · W info)
```

If you posted comments, also list the `html_url` and the anchor (`<path>:<line>`) of each posted comment. Also list each finding that you skipped as a duplicate of an existing thread, with the `html_url` of that thread.
