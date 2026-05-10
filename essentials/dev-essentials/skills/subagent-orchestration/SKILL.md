---
name: subagent-orchestration
description: How the main agent dispatches work in long, multi-step, or complex tasks. Use when running multi-stage workflows (feature-pipeline, review-loop, audit-team, PR-comment processing, multi-commit fix stacks) and when deciding whether to dispatch a subagent versus inline. Encodes four interlocking rules — orchestrate aggressively (delegate even small research), pass user-supplied context verbatim (don't pre-research to enrich prompts), prefer foreground (background only for structured-pipeline parallel siblings), and delegate high-volume external-system MCP work to subagents by default. Triggers on requests like "orchestrate this", "dispatch a subagent", "run the pipeline", "process PR comments", "review the branch", "audit the change", "handle this multi-stage task", or any session where the agent is about to inline work in the middle of a multi-stage workflow.
---

# Subagent Orchestration

Multi-stage tasks (feature-pipeline, review-loop, audit-team, PR-comment processing, multi-commit fix stacks) succeed or fail on how the main agent decides what to delegate, what to inline, and how to brief. This skill consolidates four rules the user has corrected the main agent on enough times that they belong here, not just in personal memory.

## Rule 1 — Orchestrate aggressively; delegate even small research

For multi-step, long-running, or complex work the main agent acts as orchestrator, not implementer. Each logical work unit is dispatched to a subagent. Research is NOT exempt — even a "quick" `Grep` or two `Read`s to inform planning belongs in a subagent when the parent task is multi-stage.

Self-test before any tool call inside a multi-stage session: "Could a subagent do this with a 5-line brief?" If yes, delegate. If no (genuinely needs the parent context — acknowledging the user, updating memory, dispatching another subagent) — inline.

Why: subagents preserve the main context budget, parallelise well, and produce cleaner audit trails. Inline `Grep`/`Read` in the middle of an orchestration session pollutes main context and lowers cache hit-rates for downstream stages.

What inlines: standalone single-step asks (a one-line edit on a known path, a status check, a file the user just referenced), and the orchestration verbs themselves (briefing the next subagent, talking to the user, marking memory).

What delegates:

- Multi-commit fix stacks → one subagent per commit (sequential by default; parallel only when units are genuinely independent — see Rule 3).
- Codebase-wide audits, sweeps, or cross-cutting refactors → subagent.
- Plan-locking research (find a pattern, confirm a hypothesis, locate a file) inside a multi-stage session → subagent. Do NOT inline this even when the answer feels close.
- PR-comment retrieval + classification + research (anything that maps to `dev-essentials:process-pr-comments`) → two cases, layered:
  - **User asks raw** ("process PR comments", "give me a fix plan", "handle review feedback"): main dispatches a subagent briefed with the branch/PR context, the worktree path, the skill to invoke, and the explicit deliverable ("classified threads + fix plan, do NOT implement"). The subagent runs the skill, does all external-system MCP calls, and returns the structured plan to main.
  - **User explicitly invokes `/dev-essentials:process-pr-comments`**: the skill loads and orchestrates from main; its internal phases (thread fetch, classify, per-thread research) still delegate to subagents — main never runs the high-volume external-system MCP reads inline. The distinction is where the skill entry point lives, not whether subagents are used.
  - In both cases, zero-thread PRs do not exempt: the discovery itself should have been a subagent.

## Rule 2 — Pass user-supplied context verbatim; do not pre-research to enrich it

When the user provides context before the main agent dispatches subagents — finding counts ("25 issues"), file lists ("3 clients, ignore SMS"), path patterns, scope guards, exact line refs — quote it straight into the subagent's prompt. Do NOT spawn your own grep/glob/read calls to verify the user's numbers, enumerate the files, or pre-read source to compose a "richer" brief.

Why: self-research before delegation burns the main agent's context window on facts the subagent can rediscover quickly inside its own context. The main agent then has fewer tokens for the orchestration decisions only it can make. The user has called this out explicitly: pre-research pollutes context and reduces work quality.

Heuristic: before each pre-dispatch tool call, ask "did the user already tell me this, or could the subagent learn it equally fast?" If yes, skip.

Acceptable exceptions:

- Light sanity check that protects against a catastrophic dispatch (e.g., one `git status` to confirm the worktree is clean before asking a subagent to commit).
- Genuine ambiguity in the user's wording — clarify with a question, don't research around it.

Anti-pattern: "let me preload the PR metadata so the subagent's prompt is richer" — no. Pass IDs and let the subagent fetch.

## Rule 3 — Foreground by default; background only for structured-pipeline parallel siblings

**Default: foreground.** Bash commands, single Agent dispatches, and any subagent whose output a later step needs immediately — always foreground. The user sees progress live and can intervene before completion.

**Exception (structured pipelines only):** background-parallel for genuinely independent sibling stages. Specifically the feature-pipeline `docs + code-review + security-review` triple at stages 6+7+8 (and equivalent fan-outs in review-loop / audit-team). Use `run_in_background: true` on each, all launched in a single assistant message.

Prerequisites that MUST hold simultaneously before backgrounding:

1. **Independent reads.** Every backgrounded sibling only reads shared state. No write-write or write-read race between siblings.
2. **Distinct write paths.** Each sibling writes to a different artifact path. No two backgrounded siblings touch the same file.
3. **Self-contained prompts.** Background agents cannot ask the parent for clarification mid-run, so the prompt must answer every plausible question up front — full project context, full task context, exact file paths, exact verification commands, exact reporting format.
4. **No same-message downstream dependency.** The next stage that consumes a backgrounded artifact runs only after all relevant task notifications have arrived.
5. **Single-message launch.** All siblings in one assistant turn with multiple `Agent` tool calls. Sequential launches across turns waste parallelism.

If ANY prerequisite fails, run foreground.

Notification handling (background only):

- Do NOT poll, sleep, or call any "check progress" tool. The runtime delivers a `<task-notification>` system message when each background agent completes.
- Hold the next pipeline step until all expected siblings have reported.
- If a backgrounded agent never finishes (clearly stuck, e.g. > 15 min for a stage that should take 2-5 min), report it to the user — do not silently abandon or restart.

Hard "stay foreground" cases:

- **Bash:** never set `run_in_background: true` on Bash. Long-running commands stay in the foreground; if a command runs absurdly long, that's a signal of a real problem, not a reason to background it.
- **SendMessage to an idle teammate:** never. SendMessage to an agent without an active task auto-resumes them in the background — equivalent to `run_in_background: true`. Always spawn a fresh foreground Agent run instead.
- **Any single-stage agent.** Implementation, requirements, spec, finalization — all foreground. Even when they take many minutes, the user wants progress visibility.

Ad-hoc parallel agents (NOT a pipeline): if you have 2+ independent agents to dispatch outside a structured pipeline skill, prefer **foreground parallel** (multiple Agent calls in one assistant message WITHOUT `run_in_background: true`). The runtime runs them concurrently and the response waits for all of them. You get parallelism without the progress-hiding properties of background. This matches the `superpowers:dispatching-parallel-agents` skill, which is foreground-parallel by design.

## Rule 4 — Delegate high-volume external-system MCP work to subagents by default

By default, dispatch high-volume external-system MCP work (anything that hits `mcp__plugin_github_github__*` or similar external-system MCP server tools — read OR write for operations involving large payloads or iteration) to a subagent so the main agent's context stays clean.

The main agent operates external-system MCP tools directly only when:

1. The user has explicitly asked it to ("post the replies yourself", "create the issue directly", "do the push yourself"), OR
2. A single, surgical, low-volume call is needed to unblock the next subagent (e.g., a specific PR's metadata that the subagent prompt needs inlined). Even then, prefer asking the subagent to fetch.

This applies to BOTH read-side (list threads, get PR by ID, get repo, search issues) and write-side (post reply, resolve thread, create issue).

Why: PR-thread payloads are large. Even with minimal options, fetching threads for a 20+ comment PR pollutes the main agent's context with comment HTML, identity blobs, `_links` arrays — much of which the main agent doesn't need to make orchestration decisions. Subagents read them, classify, and report back the small structured summary the main agent actually consumes.

If an external-system MCP server is missing in the current session, ask the user to fix it (`/mcp`) — never silently fall back to REST APIs or CLI tools. The main agent's repair surface (visible MCP errors, request to reconnect) is the right place to handle this.

What this rule does NOT change:

- Push commands stay with main agent because they're one-shot, low-payload, and the user's repair surface (force-push prevention, branch checks) is naturally inspectable in main.
- The user-context-passthrough rule (Rule 2) still holds — pass IDs verbatim without pre-fetching.
- Single-call ops with no thread iteration (e.g., get one PR's status) are acceptable in main — the payload is small and the call is one-shot.

Worked example: main dispatched a verify-only subagent (correct). User then said "post replies (DO IT by yourself) and push (1 command, do it by yourself)" — the explicit-ask exception applied. Main ALSO inlined a full thread-list fetch (full response, 5 threads) to get timestamp values for reply anchors — that was the mistake, polluting main context with data the subagent could have surfaced. Corrected pattern: verify-only subagent fetches threads AND returns timestamp values in its structured report; main receives only the small summary and either posts directly (explicit ask) or dispatches another subagent to post.

## Brief quality matters more than brief count

A vague brief produces shallow work. Each delegation must include:

- **What's done** so far in this session (paste the relevant context, don't paraphrase).
- **What to do** (the deliverable, in concrete terms — file paths, expected outputs).
- **What NOT to do** (scope guards, "do not implement", "do not edit X").
- **Skills the subagent must invoke** (e.g., `dotnet-backend-dev:create-tests` before writing tests).
- **The verification commands** that prove the work is done (build commands, test filters).
- **Reporting format** (what the subagent's final message should contain).
- **STOP-and-report condition** for ambiguous cases.

A 10-line brief that prevents one wrong dispatch is worth more than three 3-line briefs that each need to be redone.

## Trust but verify

Subagent reports describe intent, not necessarily reality. When the user is about to act on a recommendation:

- Re-read critical files yourself.
- Run the actual build/test if the subagent claimed green (especially after a rebase — see `dev-essentials:dotnet-build-test`).
- Never propagate "pre-existing failures" claims without ownership (see `dev-essentials:engineering-discipline` Rule 1).

## Anti-patterns

- "I'll just fetch the threads in main to see what we're dealing with." — STOP. The subagent can fetch.
- "Subagents can't use MCP tools — main agent has to post." — wrong; subagents can call MCP tools when the schemas are loaded.
- "Let me preload the PR metadata for the subagent's prompt." — no; pass the IDs and let the subagent fetch.
- "I'll do it myself in main since the user said `proceed` or `continue`." — only `do it yourself` (or equivalent explicit phrasing) is the explicit ask.
- Backgrounding a sequential stage. The notification arrives too late; the next stage reads a missing or stale file.
- Backgrounding when only one independent sibling exists. There's no parallelism win; foreground is strictly better.
- Polling background agent state with sleep loops. The runtime's notification mechanism is the correct signal.
- Using `run_in_background: true` on Bash for "convenience". Always foreground.
- SendMessage to an idle teammate to dispatch ad-hoc work. Use a fresh `Agent` call instead.
