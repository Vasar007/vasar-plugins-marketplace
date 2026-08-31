---
name: subagent-orchestration
description: How the main agent dispatches work in long, multi-step, or complex tasks. Use when running multi-stage workflows (feature-pipeline, review-loop, audit-team, PR-comment processing, multi-commit fix stacks) and when deciding whether to dispatch a subagent versus inline. Encodes seven interlocking rules — orchestrate aggressively (delegate even small research), pass user-supplied context verbatim (don't pre-research to enrich prompts), dispatch independent work concurrently via multiple Agent calls in one message (there is no separate foreground/background choice for the Agent tool), delegate high-volume external-system MCP work to subagents by default, never register subagents as named teammates (pure unnamed one-shot dispatches only), brief every write-capable dispatch with the explicit absolute worktree path, and never dispatch a pass-through delegator — an agent handed a concrete, bounded task does that work itself instead of re-delegating it. Also ships the model-selection matrix these dispatches use (Sonnet default, Haiku mechanical-only, Opus planning/review, Fable exceptional-only), so model choice does not depend on any global or repo CLAUDE.md. Triggers on requests like "orchestrate this", "dispatch a subagent", "run the pipeline", "process PR comments", "review the branch", "audit the change", "handle this multi-stage task", or any session where the agent is about to inline work in the middle of a multi-stage workflow.
---

# Subagent Orchestration

Multi-stage tasks (feature-pipeline, review-loop, audit-team, PR-comment processing, multi-commit fix stacks) succeed or fail on how the main agent decides what to delegate, what to inline, and how to brief. This skill consolidates seven rules the user has corrected the main agent on enough times that they belong here, not just in personal memory. It also owns the model-selection matrix those dispatches use — shipped here rather than assumed from a personal global `CLAUDE.md`, so the skill stands alone in any session, for anyone who installs it.

## Model selection

Every dispatch carries a `model`, and picking it is part of the orchestration decision — not an afterthought. This is the matrix the rules below mean whenever they say "per the model matrix". It ships with this skill, so model choice never depends on a global or per-repo `CLAUDE.md` being present.

| Model | When to use | Typical tasks |
| --- | --- | --- |
| **Sonnet** | Default. The executor for coding work, and a capable orchestrator. | General work; writing/editing code; executing an already-approved plan inside subagent sessions; running the orchestration itself. |
| **Haiku** | Routine, no-thinking work: read, extract, and mechanically apply. | Extracting information out of logs, tickets, or tasks; applying an explicit 1-2-3 edit list; lookups. See "Haiku scope" below. |
| **Opus** | Planning and judgment — any task that requires building a plan or thinking a design through. | Designing an implementation approach before coding; planning the fix for a review finding; reviewing a change. |
| **Fable** | Exceptional cases only — heavy multi-step planning or research. | Building a complex plan; reviewing a large or critical-path change set. Reserve for genuine need. |

**The user's explicit choice outranks this matrix.** When the user names a model for a task, use it — regardless of what the matrix, or any skill's own defaults, would otherwise pick. When the user has changed the session's own model, leave it changed; never "correct" it back toward a default.

**Fable is never dispatched silently.** When the matrix makes Fable eligible on the agent's own initiative — as opposed to the user naming it — ask the user before dispatching it, every time.

### How a model gets applied

- A session does not switch its own model mid-conversation. Whatever model the session is running, it keeps.
- Every other model is reached by **dispatching a subagent with the `Agent` tool's `model` parameter** — never via `/model`. Use the names that parameter accepts (at the time of writing `sonnet` / `opus` / `haiku` / `fable`, plus any newer ones the tool exposes).
- Therefore **any model other than the session's own must be delegated**: when the matrix, a skill, or the user's instruction calls for a different model than the session is running, that work becomes a subagent dispatch.
- **`subagent_type: "fork"` ignores `model`** — a fork inherits the parent's model. When a specific model is required, use a non-fork agent type.

### Plan → execute split

1. **Plan on Opus.** Dispatch an Opus subagent to build the plan, unless the session is already running Opus itself.
2. **Execute on Sonnet.** The session dispatches the approved plan across separate Sonnet subagent sessions instead of implementing it in one place — that is Rule 1, applied to a plan's tasks like any other work unit.

### Haiku scope (mechanical execution only)

Haiku is not limited to one-step lookups: prefer it — rather than defaulting to Sonnet — for short action sequences that carry **no synthesis of their own**, where every decision is already made and the subagent only runs the steps.

- **Haiku-eligible:** push a branch and open the PR when the commit message and PR description are already composed; post an already-drafted comment; re-run a known command and report its output; apply an explicit 1-2-3 edit list.
- **Guardrail — the content must already be decided.** If the dispatch has to *produce* the content first — draft a summary comment by reading and synthesizing several days of multi-PR work, or work out which values are correct — that is not mechanical. Keep it on Sonnet, or Opus when it is closer to planning/judgment. Eligibility comes from the content being pre-decided, never from which tool gets called — there is no blanket Haiku rule for PR creation or issue updates.
- **Worked contrast:** "push `<branch>` and create the PR from the description already composed above" → **Haiku**. "Summarize this task's work across 3 PRs and 4 days, then post it as the closeout comment" → **Sonnet**.
- **One dispatch, one model.** If a single dispatch does both the drafting and the delivery, it stays on Sonnet. Split into a Sonnet-draft + Haiku-post pair only when the draft is already a separate finished artifact — never manufacture an extra dispatch just to reach for Haiku.

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

**A phase that itself orchestrates is its own dispatch.** Any step whose own execution model is "dispatch N further subagents and coordinate their output" is a separate phase, dispatched by the orchestrating session after the previous phase's report has arrived — never folded into the previous phase's brief to save a round trip. Running `dev-essentials:review-loop` is the canonical case: it is not "more implementation work", it dispatches its own reviewer and its own fixer. Bundling "implement this, then review-loop it" into one brief hands that second layer of fan-out to the implementer (`main → implementer → its own reviewer/fixer`) and deletes the one checkpoint that matters: the orchestrator reading the implementation report, and verifying the commit, before review starts. This cuts with Rule 1's grain rather than against it — more dispatches, each one phase wide.

The pattern to copy already ships in this plugin: `dev-essentials:research-implement-review-report` keeps Phase 2 (Implement) and Phase 3 (Review loop) as two separate phases, both driven by the orchestrating session, for exactly this reason. Follow that shape; do not invent a bundled variant of it.

Self-test before sending any multi-step brief: "does any step in this brief require the agent to dispatch its own subagents?" If yes, cut the brief at that step and make it your own next dispatch.

**Describe the dispatch you actually made.** What the orchestrating session tells the user it delegated must match the text of the brief it sent. Never summarize a narrower scope than what the subagent was actually told to do — no "dispatched steps 1-5, I'll handle step 6 myself later" when steps 6 and 7 sit verbatim in that same prompt. A summary of a dispatch is a checkable claim about the prompt, not a recollection of intent: re-read the brief before describing it. If the brief turns out broader than intended, the fix is to dispatch a narrower one — never to describe it as narrower than it is.

This rule governs the orchestrator's handoff decision only; what a receiver does with a concrete, bounded task is Rule 7's. The two meet in the phase-bundling case above: a bundled brief and a pass-through delegator produce the same shape — `main → agent → agent's own dispatches`, with no orchestrator checkpoint — but the defect belongs to a different party. Shorten the brief here; do not rely on the receiver refusing it under Rule 7.

Worked example — bundled review loop: an orchestrating session dispatched ONE subagent with a seven-step brief — research the patterns behind a design decision, pick a design, implement it, build/test/commit as one commit, then run `dev-essentials:review-loop` scoped to everything since a given baseline and amend its fixes into that commit, and do not push. It then told the user: "I've dispatched the implementation subagent (steps 1-5) … I'll wait for its completion notification before proceeding to the review loop (step 6)." Two defects in one dispatch. Step 6 is an orchestration phase — it fans out to a reviewer and a fixer — so it was the orchestrator's own next dispatch, to be made after the implementation report arrived; folded into the implementer's brief it became `main → implementer → reviewer + fixer` with no orchestrator checkpoint between implementing and reviewing. And the summary claimed a steps-1-5 scope while the prompt itself already contained 6 and 7. Correct pattern: dispatch steps 1-5, receive the report, verify the commit, THEN dispatch the review loop as the orchestrator's own next phase — and report the scope as steps 1-5 only because that is genuinely all the brief said.

## Rule 2 — Pass user-supplied context verbatim; do not pre-research to enrich it

When the user provides context before the main agent dispatches subagents — finding counts ("25 issues"), file lists ("3 clients, ignore SMS"), path patterns, scope guards, exact line refs — quote it straight into the subagent's prompt. Do NOT spawn your own grep/glob/read calls to verify the user's numbers, enumerate the files, or pre-read source to compose a "richer" brief.

Why: self-research before delegation burns the main agent's context window on facts the subagent can rediscover quickly inside its own context. The main agent then has fewer tokens for the orchestration decisions only it can make. The user has called this out explicitly: pre-research pollutes context and reduces work quality.

Heuristic: before each pre-dispatch tool call, ask "did the user already tell me this, or could the subagent learn it equally fast?" If yes, skip.

Acceptable exceptions:

- Light sanity check that protects against a catastrophic dispatch (e.g., one `git status` to confirm the worktree is clean before asking a subagent to commit).
- Genuine ambiguity in the user's wording — clarify with a question, don't research around it.

Anti-pattern: "let me preload the PR metadata so the subagent's prompt is richer" — no. Pass IDs and let the subagent fetch.

## Rule 3 — Agent dispatch has no foreground/background choice; dispatch independent work concurrently

**Fact, not preference:** the `Agent` tool has no synchronous "foreground" mode to opt out of. Its parameter schema is `description`, `isolation`, `mode` (deprecated), `model`, `name`, `prompt`, `subagent_type`, `team_name` — there is no `run_in_background` field — and the tool's own description states plainly: "Subagents run in the background; you'll be notified when one completes." Every `Agent` dispatch returns immediately; the subagent's result arrives later via a task notification. There is nothing left to "prefer foreground" over for the `Agent` tool specifically — that choice does not exist.

This is specific to `Agent`. `Bash` and `PowerShell` still have a real `run_in_background` parameter and a genuine synchronous-vs-background choice — nothing here changes guidance for those two tools.

**Parallelism is still the goal.** Dispatch independent work concurrently by making multiple `Agent` tool calls within a SINGLE assistant message — that is what produces real concurrent execution: all agents launch together, and you receive separate task notifications as each completes. This skill calls that pattern "foreground-parallel" dispatch — it is the only way to parallelize independent `Agent` calls, since the `Agent` tool has no background mode to contrast it with.

**Genuine sequential dependency** (stage B needs stage A's output) still means: dispatch A, wait for A's task notification, then dispatch B in a later message. Nothing about this changes.

**Never poll, sleep, or call any "check progress" tool** while waiting for a dispatched agent. The runtime delivers a task notification when each agent completes — that is the correct signal, not a substitute loop.

Cases that don't change:

- **Bash/PowerShell:** never set `run_in_background: true` on Bash for "convenience" — that flag genuinely exists there and is a real choice. Long-running Bash/PowerShell commands stay foreground; if a command runs absurdly long, that's a signal of a real problem, not a reason to background it.
- **SendMessage to an idle teammate:** never. SendMessage to an agent without an active task auto-resumes them in the background. Always dispatch a fresh, unnamed `Agent` call instead (see Rule 5 — named/addressable teammates are themselves out of scope for one-shot delegation).

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

## Rule 5 — No `name`/`team_name`/SendMessage coordination for one-shot delegation

Never pass the `Agent` tool's `name` parameter for a one-shot delegation. `name` registers the subagent as an addressable, long-lived teammate: it can be resumed later via `SendMessage`, and it emits extra `teammate-message`/`idle_notification` event traffic into the session. That is the wrong shape for "do this, report back, done." Use pure, unnamed subagents — the dispatch returns the agent's final message directly, and that's the end of the interaction.

Never use `team_name`. Never coordinate multiple subagents via `SendMessage`, and never use `TaskCreate`/`TaskUpdate`/`TaskList` (or `TodoWrite`) as a SHARED task list between subagents with `owner`/`blockedBy` ownership semantics — that is team coordination, not delegation, and it's out of scope regardless of how convenient it looks for a multi-agent fan-out. (Using those same tools SOLO in the orchestrating session to track your own progress on a task, for the user's visibility, is fine — that is not what this rule forbids.)

The correct dispatch shape has exactly these fields:

```text
Agent(
    subagent_type: "...",       # or a specific agent type
    model:         "...",       # per the model matrix
    description:   "Short 3-5 word label",
    prompt:        "<complete, self-contained brief>"
)
# no name, no team_name
```

Everything the subagent needs goes in `prompt`, because there is no way to talk to it again afterward — so the brief must be fully self-contained (see "Brief quality matters more than brief count" below). If a subagent finishes without delivering a usable result, do NOT try to resume it — verify the work directly, or dispatch a fresh subagent.

## Rule 6 — Worktree-path discipline for write-capable dispatches

Every write-capable subagent dispatch (one that will edit files or run git commands) must carry the ABSOLUTE worktree path explicitly — in the first few lines of the brief, and again at every concrete instruction that touches files. A dispatched subagent's shell CWD is the MAIN repo root, NOT whatever worktree the orchestrating session itself is working in. Most relative paths exist in both locations, so an ambiguous brief lets the subagent silently edit the wrong copy.

The subagent must be told to STOP and ask if no absolute worktree path was given in its brief — never assume the current working directory, never infer the worktree from a relative path mentioned elsewhere in the brief.

When two or more worktrees are in play, give an explicit CORRECT/WRONG example block near the top of the brief, e.g.:

```text
## Worktree (REQUIRED — read first)

CORRECT: <absolute-path-to-repo>\.claude\worktrees\<full-branch-ref>\
WRONG  : <absolute-path-to-repo>\

Most files exist in BOTH. NEVER edit anything outside the CORRECT path. Every Read/Edit/Write uses an ABSOLUTE path starting with CORRECT. Every git call uses `git -C "<CORRECT>"`.
```

Every git call inside the subagent's own work uses `git -C "<absolute-worktree-path>"` — never a bare `git` relying on inherited CWD.

Two verification gates belong in every such brief:

- **Pre-flight** (the subagent's first action): `git -C "<worktree>" rev-parse --abbrev-ref HEAD` matches the expected branch name. STOP if not.
- **Post-edit** (after each edit batch): `git -C "<main-repo-root>" status --porcelain` comes back clean — confirming nothing leaked outside the intended worktree.

No `.bak` files — the Edit tool already fails loudly on a content mismatch, so manual backups are unnecessary and pollute the tree.

This rule is about briefing dispatched subagents correctly. Worktree creation/lifecycle mechanics (creating, listing, removing worktrees) belongs to `dev-essentials:git-worktree-management`, not this rule.

## Rule 7 — Do the work you were dispatched to do; no pass-through delegators

An agent handed a concrete, bounded task DOES that task. Re-dispatching it to a fresh subagent and then only relaying that subagent's report is a no-op hop: it buys no parallelism, protects nothing (the parent has nothing to protect here — its own context was already sized for the job), and costs a full brief rewrite plus another notification round-trip. This binds every level — the main session, and any subagent that was itself handed a concrete task.

Self-test before any dispatch, once you are the receiver of an already-handed, bounded task: "Does MY OWN bounded task description already tell me to do the concrete work, or does the scope genuinely not fit one agent?" If the former, do it yourself. Only decompose further when the work truly exceeds a single dispatch.

Rule 1 is not a licence for a second hop. Rule 1 decides what the orchestrator hands OFF; Rule 7 decides what the receiver does with it once handed. "Delegate even small research" applies to an orchestrator facing an undivided multi-stage task — never to an agent that has already been handed the one thing to do.

Further fan-out IS legitimate when the received task is genuinely large-scale:

- Broad research or an audit spanning many files/areas that one context cannot hold.
- A multi-step sweep with independent branches that can run concurrently (see Rule 3).
- A stage that splits into distinct deliverables needing different skills or models.

The test is whether each child dispatch owns real, separable work — not whether the parent would prefer someone else typed the commands.

**Brief accordingly.** When dispatching concrete work, state it in the brief: "do this work yourself; do NOT dispatch further subagents for it." When the task genuinely warrants fan-out, say that instead — leaving it unstated is what produced the failure below.

Worked example — worktree cleanup: an orchestrating session loaded `dev-essentials:git-worktree-management`, then dispatched a subagent to remove a merged worktree and its branch for a completed task — correct so far. That subagent's entire brief WAS the concrete work: confirm the merge, salvage anything worth keeping, run `git worktree remove`, delete the branch. Instead it dispatched another subagent for exactly that scope and reported back: "I've dispatched a subagent to handle the worktree/branch cleanup. It's running now — I'll report back once it completes." Actual chain: `main → agent → agent`. Correct chain: `main → agent`, with that agent performing the removal itself. The inner dispatch carried no decomposition — same scope, same paths, one extra hop and zero work done by the agent that owned the task.

## Brief quality matters more than brief count

A vague brief produces shallow work. Each delegation must include:

- **What's done** so far in this session (paste the relevant context, don't paraphrase).
- **What to do** (the deliverable, in concrete terms — file paths, expected outputs).
- **What NOT to do** (scope guards, "do not implement", "do not edit X").
- **Skills the subagent must invoke** (e.g., `dotnet-backend-dev:create-tests` before writing tests).
- **The verification commands** that prove the work is done (build commands, test filters).
- **Reporting format** (what the subagent's final message should contain).
- **STOP-and-report condition** for ambiguous cases.
- **Whether further fan-out is allowed** — for a concrete, bounded task, say "do this yourself; do NOT dispatch further subagents" (see Rule 7).

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
- Dispatching a sequential-dependency stage before its predecessor's task notification has arrived.
- Splitting one independent task across multiple redundant `Agent` dispatches when a single dispatch would do.
- Polling agent state with sleep loops. The runtime's task-notification mechanism is the correct signal.
- Using `run_in_background: true` on Bash for "convenience". Always foreground.
- SendMessage to an idle teammate to dispatch ad-hoc work. Use a fresh, unnamed `Agent` call instead.
- Passing `name` to the `Agent` tool for a one-shot delegation, "just in case" a follow-up is needed. It isn't — dispatch a fresh subagent instead.
- Briefing a write-capable subagent with a relative path or no worktree path at all, and hoping it infers the right one.
- "My job is the worktree removal / the one-file edit / the single command — I'll dispatch a subagent to do it and report back." — that's a pass-through delegator; do the concrete work yourself (Rule 7).
- "I'll fold the review loop into the implementer's brief — it saves a round trip." — no; a step that dispatches its own subagents is the orchestrator's own next dispatch, made after the previous phase reports (Rule 1, and Phase 2 / Phase 3 in `dev-essentials:research-implement-review-report`).
- "I've dispatched steps 1-5 and will handle step 6 myself" — when steps 6 and 7 are verbatim in that same prompt. Describe the brief you actually sent, not the one you meant to send (Rule 1).
