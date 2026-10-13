---
description: Work one task end-to-end via research-implement-review-report — after first sweeping the additional context the user brings (PR/issue links to fetch, or plain free-text notes), and after the review loop adding a mandatory /simplify pass landed as its own separate commit on top. Never pushes.
argument-hint: <issue reference or task description> [--base=<branch>] [--worktree=<branch-ref>] [--refs=<url|id|text>...] [--commit-mode=per-phase|single] [--rounds=N] [--notes-dir=<path>] [--no-simplify] [--push] [--interactive] [--autonomous]
---
<!-- markdownlint-disable MD013 -->

# Implement Task (context sweep → full cycle → simplify commit)

**Division of labour in this command family — read this before reaching for
a neighbour:** `dev-essentials:implement` runs an already-written plan file,
standalone. `dev-essentials:research-implement-review-report` (RIRR) is the
lighter, non-OpenSpec research → implement → review-loop → report cycle for
one task. **This command wraps RIRR for one task**, owns the worktree it
hands to RIRR (RIRR's Phase 0 then reduces to a verification step — see
Phase 1 below), and adds the two things RIRR deliberately does not own:

1. **An additional-context sweep before research starts.** The user usually
   arrives with a task *plus* extra context worth reading first — related PRs
   and issues that set the pattern the task must stay consistent with, or
   plain free-text instructions with nothing to fetch. Fetchable items get read
   by a subagent; free-text items are folded in verbatim. Either way it is
   handed into the wrapped command's research phase as context, so Phase 1
   builds on it instead of rediscovering (or contradicting) it.
2. **A mandatory `/simplify` pass after the review loop and before the
   report**, landed as its **own separate commit on top** of whatever the
   wrapped command produced.

Everything else — branch/worktree setup, research, the plan gate, the
implementation, the review loop, the commit mode, the handoff report — is the
wrapped command's job and is **not** reimplemented here.

Use `dev-essentials:implement-batch` instead when there are N tasks to work as
a commit stack. Use `dev-essentials:research-implement-review-report`
directly when there is no additional context to sweep and no simplify pass
wanted.

**Arguments**: $ARGUMENTS

- Format: `<issue reference or task description> [options]`
- Examples (illustrative only — no issue number, branch, PR link, author, or
  note text below is hardcoded behavior):
  - `Issue 123456: add pagination support to the invoice export endpoint --base=main --refs=https://github.com/acme/billing-service/pull/482 --refs=https://github.com/acme/reporting-service/pull/510 --refs=1201`
  - `Bug 987654 — checkout fails on cross-region currency conversion --base=release/2.0 --refs=1188`
  - `Issue 123456: add the retention option --base=release/2.0 --worktree=vvasilyev/tasks/123456-retention-option --commit-mode=per-phase`
  - `Issue 123456 ... target branch is release/2.0. Related PRs worth reading
    first: <url>, <url>, plus issue <id>.` — the same thing in prose;
    references named in prose count exactly as `--refs` values.
  - `Issue 456789: add the retry option --base=release/2.0 --refs=https://github.com/acme/payments-service/pull/641 --refs="follow the retry pattern already used in the notification client, not the old batching one"` —
    mixing a fetchable PR link with a plain free-text instruction in the same
    `--refs` list.
  - `Issue 123456: tidy up the option plumbing --base=release/2.0 --no-simplify`
- **The context list is arbitrary and optional** — zero, one, or many items,
  each either a fetchable URL/ID (a PR, an issue, a document, a wiki page)
  or a plain free-text note, in any order, from any repo, tracker, or nowhere
  at all. Zero context items is a normal run: Phase 2 becomes a no-op and says
  so.
- If no arguments, use the **AskUserQuestion** tool to ask what to work on.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`/`master`/`develop`. See Phase 0. |
| `--worktree=<branch-ref>` | ask or derive | Branch ref for the worktree this run happens in. Use the value given here, or one named in prose in $ARGUMENTS, verbatim. Otherwise derive it using the branch-name table in `dev-essentials:research-implement-review-report`'s Phase 0 (that table is the single source of truth — it is not restated here), taking the `<prefix>` from the branch-naming convention documented in the repo's or the user's `CLAUDE.md`, and **ask once** if no convention is documented. |
| `--refs=<url\|id\|text>` | none | Additional context for this run. Repeatable, and additive with anything named in prose. Each value is either **a URL or ID** — a PR, issue, document, wiki page, or any other fetchable reference, fetched via whichever MCP/web-fetch tool matches its host before research starts — or **plain free text**, an instruction or note with nothing to fetch (e.g. "avoid the retry-wrapper pattern used in the old client"), used verbatim. Which one a value is comes from how it reads, not from a tag the user has to supply. Read-only either way — see Phase 2. |
| `--commit-mode=<per-phase\|single>` | `single` | Forwarded verbatim to `dev-essentials:research-implement-review-report`'s own `--commit-mode`. This wrapper defaults to `single` (the wrapped command's own default is `per-phase`) because the intended end state is one clean task commit plus one simplify commit. Either mode works; see Phase 4 for how the simplify commit sits on top of each. |
| `--rounds=<N>` | `2` | Review-loop cycles. Forwarded verbatim to the wrapped command's `--rounds`. |
| `--notes-dir=<path>` | `Notes/` | Root (inside the worktree) for this run's artifacts, with subfolders as needed: `Notes/Research/` for Phase 2's context document, `Notes/Plans/` for the plan, `Notes/Results/` for the report. The repo's `CLAUDE.md` convention wins over this default. |
| `--no-simplify` | off | Skip Phase 4. **Off by default on purpose — the simplify pass is a standard part of this command, not an add-on.** Pass this only for a run where the user has said they don't want it. |
| `--push` | off | Push after the final report. **Off by default and off unless the user asks for it in this invocation** — the default contract is commit locally, report, and wait for the user's review. |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

Any option not listed above that the wrapped command accepts (`--context`,
`--skip-research`, `--branch-prefix`) is passed straight through, with one
exception: Phase 2 owns `--context` when it produces a context document
(see Phase 3), so a user-supplied `--context` is **added to**, never replaced
by, Phase 2's document.

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
- With `--autonomous`, do not destroy git work that has no other copy. Examples: commits that no other branch or remote holds (such as `git branch -D` on an unmerged branch), and uncommitted changes (such as a worktree removal that has uncommitted changes). Do not do such an action. List it in the final report. A context file that a cleanup step of this workflow classifies for deletion is not covered by this rule.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Subagent dispatch

Every phase below dispatches subagents per
`dev-essentials:subagent-orchestration` — read that skill before
starting. It owns the dispatch rules (concurrent multi-`Agent`-call dispatch
for independent work), the no-`name`/no-teams rule, the
delegate-external-MCP-by-default rule, the absolute-worktree-path rule, and
brief-quality discipline; this command does not restate them.

### You are the orchestrator, not the executor

The whole point of running a task this way is to still have context left at the
end of it:

- **Delegate aggressively — including the work that feels too small to
  delegate.** Reading a fetchable reference's diff, checking how a pattern is
  used, confirming a file's current shape: all of it is a subagent's job, not
  the orchestrating session's. Per
  `dev-essentials:subagent-orchestration` Rule 1, the self-test is
  "could a subagent do this with a 5-line brief?" — if yes, it is delegated.
- **What the orchestrating session actually does, and nothing more:** resolve
  arguments, ask the user the Phase 0 questions, create the worktree, dispatch,
  read the compact structured reports that come back, run the git bookkeeping
  (SHA recording, the Phase 4 commit), and talk to the user. It never greps or
  reads source to "understand the task" first, fetches PR/issue payloads
  inline, writes or edits product code, or reviews a diff itself.
- **Every brief asks for a compact structured report** — verdicts, `file:line`
  anchors, the commands run and their actual results — never pasted diffs, file
  dumps, or PR comment HTML. That, plus Rule 2 (pass the user's context
  verbatim; do not pre-research to enrich a brief), is what keeps a long task
  survivable in one session.

Additions specific to this command:

- **Model per stage**: the additional-context sweep is judgment work about how
  code should fit together, so it uses **Opus**; pure mechanical extraction
  (pulling an issue's description/acceptance criteria out of the tracker,
  listing a PR's changed file paths, or simply carrying a free-text note
  verbatim) may use **Haiku** instead, per Phase 2's own callout below; the
  wrapped command owns its own per-stage model choices for
  research/implement/review, and this command does not override them. All per
  the model matrix in the "Model selection" section of
  `dev-essentials:subagent-orchestration`.
- Fable is exceptional-only. Never dispatch it silently on the agent's own
  initiative. With `--interactive`, ask first, every time, also where the model
  matrix marks Fable as eligible. Without it, follow "Autonomy".
- **Every concrete, bounded dispatch is briefed to do the work itself, not to
  re-delegate** — read this one fetchable reference, run this one simplify
  pass — per
  `dev-essentials:subagent-orchestration` Rule 7 (no pass-through
  delegators). State it in the brief: "do this work yourself; do NOT dispatch
  further subagents for it."

## Progress tracking for the user

Seed a tracking list (`TodoWrite`, or `TaskCreate`/`TaskUpdate`/`TaskList` —
use whichever this session actually has; on newer models these are opt-in, so
don't assume) with one entry per phase, and flip each as it happens. Solo
progress tracking for the user's visibility only — never as a coordination
channel between subagents (that stays banned per
`dev-essentials:subagent-orchestration`).

## Phases

### Phase 0 — Resolve the ask

1. Parse from $ARGUMENTS, verbatim: the issue reference or task
   description; the base branch; the worktree branch ref; every context item
   (from `--refs` and from prose alike) — each one is either a fetchable
   URL/ID or a plain free-text note, sorted per the Options table's `--refs`
   description; any scope guard the user stated. Pass all of it verbatim into
   every subagent brief — do not pre-research to "enrich" it (Rule 2).
2. Resolve `--base` and `--worktree` per the Options table.
3. **Echo back, in one short block before any work starts:** the task, the base
   branch, the worktree branch ref, the resolved context list, the commit
   mode, and whether the simplify pass will run. A mis-read context list or a
   wrong base branch is cheap to correct here and expensive later.
4. **If anything material is missing or ambiguous — which task, which branch,
   the worktree name, which of two readings of the task applies, or whether a
   pasted link is meant as context or as the thing to change — use the
   AskUserQuestion tool now, before any work starts. If nothing is unclear,
   start working without a confirmation round-trip.** (This is the user's own
   standing instruction for this workflow: ask first if there are questions,
   otherwise begin.)

### Phase 1 — Worktree setup

Create the worktree per `dev-essentials:git-worktree-management`
(if the run has `--interactive` or `--autonomous`, pass it on),
branching from the Phase 0 base branch, and run its post-create bootstrap.
Record its **absolute path** — every write-capable dispatch from here on
carries it explicitly, per `dev-essentials:subagent-orchestration`
Rule 6, and every git call uses `git -C "<abs worktree path>"`.

**Why this command creates the worktree rather than leaving it to the wrapped
command's Phase 0:** Phase 2 has to run *before* the wrapped command starts,
and it both reads base-branch code (to see how a fetchable reference's changes
relate to the code this task will touch, or to check a free-text note's
pointer to an existing pattern) and **writes** its context document to
`<--notes-dir>/Research/`, which must already be inside the worktree for the
wrapped command's Phase 1 to read it. So the worktree has to exist first.

Phase 3's invocation passes the already-resolved base branch, branch name, and
absolute worktree path explicitly, so the wrapped command's Phase 0 reduces to
a **verification** step — confirm
`git -C "<worktree>" rev-parse --abbrev-ref HEAD` matches the expected branch —
and must **not** re-derive a name or create a second worktree/branch.

Then record `RUN_BASE_SHA = git -C "<worktree>" rev-parse HEAD`. Phase 4 and
Phase 5 both need it.

### Phase 2 — Additional context sweep (skipped when none is given)

Sort the Phase 0 context list into two kinds before dispatching, by how each
item reads rather than by a tag the user supplied: items that look like a URL
or ID (fetch them) and items that read as prose (use them as-is, nothing to
fetch).

Dispatch **Opus subagent(s)** to fetch every fetchable item and return
structured findings: one subagent when there is a single fetchable item (or
none), or **foreground-parallel** — multiple `Agent` calls in one message —
when the fetchable items are genuinely independent (different repos, unrelated
issues, unrelated pages). **Exception:** a sub-dispatch that is purely
mechanical extraction — e.g. just pulling an issue's title/description with
no synthesis — may use **Haiku** instead of Opus. Each dispatched subagent's
deliverable is ONLY the structured summary in its own final message — never a
file write, so parallel dispatches never collide on the same path. **The
orchestrating session writes the single consolidated context document itself**,
which is exactly the kind of "orchestration verb" that inlines rather than
delegates, per `dev-essentials:subagent-orchestration` Rule 1's "what
inlines" list.

Brief requirements:

- The absolute worktree path, the base branch, the task text verbatim, and the
  full context list verbatim, with each item already sorted into fetchable or
  free-text.
- **Read-only scope guard: do not edit, create, or delete any product file; do
  not create, comment on, update, or vote on any PR, issue, or document.**
  This dispatch writes no file at all.
- **Tracker/document access is the subagent's job, not the orchestrating
  session's** — per `dev-essentials:subagent-orchestration` Rule 4. Use
  whichever MCP or web-fetch tool the item's host actually has available.
  GitHub is the tracker with documented conventions in this plugin
  (`dev-essentials:github-mcp-conventions`) — load that skill for any
  GitHub PR, issue, or file-content fetch; for any other host with an MCP or
  fetch tool (a wiki, a document store, a different tracker), use it
  directly, and if a fetchable item's host has **no** fetch mechanism
  available in this session, say so and ask the user rather than silently
  skipping the item or falling back to raw REST calls. **Free-text items
  are never fetched** — carry them through verbatim, no MCP or web-fetch call.
- The deliverable — a compact structured summary returned in the subagent's
  final message only, with two groupings:
  - **Fetched references** — one section per item: what it is, its author, its
    state (merged/active/abandoned, open/closed), its one-paragraph intent,
    and **which files and types it touched, with `file:line` anchors into the
    base branch**, and which of those overlap the area this task will change.
  - **Free-text notes** — each quoted directly, verbatim, with nothing
    invented about an author, state, or files touched — those concepts don't
    apply to a plain note.
  - Both groupings feed a shared synthesis, drawn from whichever items apply:
    - **The pattern established** — the shape a consistent implementation of
      this task should follow, stated concretely enough to plan against.
    - **Constraints and conflicts** — anything in a fetched reference or a
      free-text note that constrains this task, contradicts the task text, or
      (for a fetched reference) is already in flight and would collide.
    - **Explicitly out of scope** — what a fetched reference already does that
      this task must *not* redo.
- A STOP-and-report condition: a context item — fetched or free-text — that
  turns out to already implement the task, or that contradicts the task as
  written, is reported to the user before Phase 3 starts — not resolved
  unilaterally.

Once every dispatch returns, the orchestrating session consolidates all
returned summaries, together with the free-text items, into a single document
at `<--notes-dir>/Research/<slug>-context.md` inside the worktree, preserving
the same two groupings — never delegating that write.

Present the consolidated summary to the user in a few lines, together with any
conflict found. **With zero context items, this phase does nothing** — say so
in one line and move on; no context document is written.

### Phase 3 — Run the wrapped workflow, through its review loop

Invoke `dev-essentials:research-implement-review-report` and let it own its
Phase 0-3 exactly as written — research, the plan and its plan gate,
implementation, build/test, the review loop, and the commit cadence for the
resolved `--commit-mode`. **Do not reimplement, re-order, or second-guess any
of it**, including its review-loop configuration, which is that command's own
(this wrapper does not restate review-loop flags — follow the wrapped
command's Phase 3 configuration and, through it,
`dev-essentials:review-loop`'s own conventions).

Pass it, explicitly:

- The task text verbatim from Phase 0, as its positional argument.
- `--base=<Phase 0 base branch>` and the resolved branch name / absolute
  worktree path from Phase 1, with the instruction that its **Phase 0 is a
  verification step only** — the worktree and branch already exist; confirm and
  proceed, do not create or re-derive.
- `--commit-mode=<resolved>` and `--rounds=<N>`.
- `--interactive` or `--autonomous`, for a run that has it.
- The resolved `<--notes-dir>` as this run's **artifact root**, stated
  explicitly: the wrapped command's own `Notes/Plans/` and `Notes/Results/`
  defaults become `<--notes-dir>/Plans/` and `<--notes-dir>/Results/`. The
  wrapped command has no `--notes-dir` flag of its own — it takes the root as
  an instruction, via the same "or the repo's own documented convention" path
  its Phase 1 and Phase 4 already allow. Phase 4's own contract requires it to
  confirm to the user where the report was saved — including under the repo's
  own documented convention or a `-handoff-N.md` continuation name, not just
  the default `<--notes-dir>/Results/<slug>-report.md`. Phase 5 does not guess
  that path: it reads the exact path back from that confirmation when it
  hands control to Phase 4 (see Phase 5 below).
- `--context=<--notes-dir>/Research/<slug>-context.md` — the Phase 2
  document, **only when Phase 2 actually wrote one**. With zero context items
  Phase 2 writes no document (see Phase 2), so omit `--context` entirely rather
  than passing a path that does not exist; pass only a user-supplied
  `--context`, if there is one, or nothing at all. **This is the mechanism by
  which the additional context reaches research:** the wrapped command's Phase 1
  reads `--context` in the orchestrating session before dispatching any research
  subagent, and its
  Phase 2 already accepts a non-plan research/handoff file. Add the requirement
  that the document's findings be **passed verbatim into every Phase 1 research
  brief and into the Phase 1 plan's own "Findings" section**, so the plan is
  visibly grounded in the fetched references and free-text notes rather than in
  a parallel rediscovery of them. If the user also supplied their own
  `--context`, pass both paths — the Phase 2 document never displaces a
  user-supplied one.
- **A hard stop instruction: finish Phase 3 (review loop), including the
  `--commit-mode=single` squash if that mode is active, then STOP and hand
  control back — do not start Phase 4 (Report).** Phase 4 of *this* command has
  to land between the two, and its commit must not be swallowed by the squash.

When it hands back, record
`SIMPLIFY_BASE_SHA = git -C "<worktree>" rev-parse HEAD` — the tip of
everything the wrapped workflow produced.

### Phase 4 — Mandatory simplify pass (its own commit)

Skipped only when `--no-simplify` was passed in this invocation.

`/simplify` is an external, already-available skill (not part of this plugin):
"review the changed code for reuse, simplification, efficiency, and altitude
cleanups, then apply the fixes. Quality only — it does not hunt for bugs."
**Invoke it; do not reimplement its logic**, exactly as this command's other
phases invoke `dev-essentials:research-implement-review-report` and
`dev-essentials:review-loop` without reproducing them.

1. **Run it exactly once**, via `Skill(skill: "simplify")` (or the `/simplify`
   slash form), against **this run's implementation diff** —
   `<RUN_BASE_SHA>..HEAD` in the Phase 1 worktree. State that range explicitly
   in the invocation, since the skill's own default target is "the changed
   code" and this run's changes are already committed rather than sitting in the
   working tree. One pass, not a loop: this is a cleanup sweep, not a second
   review loop.
2. **What it is looking for**, stated explicitly when invoking it: complexity
   and over-engineering that *this run introduced* — defensive layers guarding
   failures that don't need guarding, abstractions with one caller, duplicated
   logic that an existing helper already covers, indirection that adds no
   value, and code sitting at the wrong altitude for its file.
3. **Scope guards.** In scope: making this run's own diff simpler while
   behavior stays identical. Out of scope: touching code this run didn't
   change, changing behavior or a public contract, deleting or relaxing a test
   to simplify the code under it, and "simplifying" by swallowing an error
   path. Anything that would require one of those is a **STOP and ask the
   user**, not a unilateral call (per
   `dev-essentials:engineering-discipline` Rule 2). With `--autonomous`, do not
   make that change: keep the code as it is, and list the skipped cleanup in the
   report.
4. **Re-verify before committing.** Build and run the tests again after the
   cleanup — a simplification that breaks a test is a regression this session
   owns, not a pre-existing failure (Rule 1 of the same skill). For .NET repos
   follow `dev-essentials:dotnet-build-test`: `dotnet build` is
   authoritative, IDE/LSP diagnostics are not, and builds and tests run
   foreground only.
5. **Commit it separately, on top.** Stage explicit paths — never
   `git add -A`/`git add .`:

   ```bash
   git -C "<worktree>" commit -m "<Issue ref> — simplify: <summary of cleanups>"
   ```

   This commit is **always its own commit on top** of whatever Phase 3
   produced, in both commit modes:
   - `--commit-mode=single`: on top of the single squashed commit. **Never
     `--amend` into it, and never re-run the squash after this point** — the
     end state is deliberately two commits, not one.
   - `--commit-mode=per-phase`: on top of the per-phase and per-review-round
     commits, as one additional commit.
6. **No cleanup found is a valid outcome.** If the pass changes nothing, do not
   manufacture an empty commit and do not invent cleanups to justify the phase
   — report "simplify pass found nothing worth changing" and move on.

### Phase 5 — Report and stop

Hand control back to `dev-essentials:research-implement-review-report`'s
**Phase 4 (Report)** and let it write the handoff document its own way (via
`dev-essentials:save-context`) to whichever path its own Phase 4 contract
resolves — the default `<--notes-dir>/Results/<slug>-report.md`, the repo's
own documented convention, or a `-handoff-N.md` continuation name. Do not
assume the default path: read the exact saved path back from Phase 4's own
"confirm to the user where the report was saved" output and use that value
everywhere below. Require these additions to what it reports:

- The Phase 2 context sweep: which items were read (fetched references and
  free-text notes alike), the pattern they established, how the implementation
  followed it, and any conflict that was surfaced and how it was resolved. The
  context document's path.
- The Phase 4 simplify pass: that it ran (or was skipped via `--no-simplify`),
  what it changed, its commit subject, and the post-cleanup build/test result
  as actual output rather than a claim.
- **The verified commit topology**, not the intended one:
  `git -C "<worktree>" log --oneline <RUN_BASE_SHA>..HEAD`. The expected end
  state under the default `--commit-mode=single` is **one task commit + one
  simplify commit** (or just the task commit when the pass found nothing). If
  the real topology differs, report the real one and explain why. Check Phase 4
  precisely rather than by eyeballing that log:
  `git -C "<worktree>" log --oneline <SIMPLIFY_BASE_SHA>..HEAD` must show
  exactly one commit — or zero when the pass found nothing.
- The worktree's absolute path and the branch name, so the user can review it
  directly.
- Each gate that this run or the wrapped command approved without a stop.

Print the report only. Do not print a next-session continuation prompt.

**Do not push.** Stop here and wait for the user's review. Push only if
`--push` was explicitly passed in this invocation, and even then only after the
report has been delivered.

## Guardrails

- **This is a wrapper. Do not reimplement what it wraps.**
  `dev-essentials:research-implement-review-report` owns research, the plan
  gate, implementation, the review loop and its configuration, the
  commit cadence, and the report. `/simplify` owns the cleanup pass.
  `dev-essentials:git-worktree-management` owns worktree mechanics. This
  command owns only the sequencing, the context sweep, and the simplify
  commit.
- **The simplify commit is never folded in.** No `--amend`, no re-squash after
  Phase 4. Two commits is the intended shape.
- **Context is context, never a target.** Phase 2 reads or carries it forward;
  it never changes, comments on, or votes on a fetched reference, and the
  task's own implementation does not "fix" whatever a fetched reference left
  undone unless the user asks.
- **Zero context items is normal**, and so is a fetchable item whose host has
  no fetch mechanism available — the latter is an ask, not a silent skip.
- **Ask before guessing** on a missing task reference, base branch, worktree
  name, or an ambiguous reading of the task — and then get on with it. Asking
  is the first move, not a running commentary.
- **Own every red signal** from any build or test run in this session,
  including Phase 4's — never wave one off as "pre-existing" without proving it
  predates `RUN_BASE_SHA` (per
  `dev-essentials:engineering-discipline`).
- **No unilateral critical decisions** — public-contract changes, new DI
  dependencies, test-assertion relaxations — beyond what the Phase 1 plan
  authorized. That includes anything the simplify pass proposes. With
  `--autonomous`, follow "Autonomy".
- **Never push by default** without the user's explicit go-ahead each time.
- **Artifacts live under `<--notes-dir>`** (default `Notes/`, with
  `Research/`, `Plans/`, `Results/` subfolders) inside the worktree — never
  scattered at the repo root, and never referenced from shipped code, docs, or
  commit messages (per
  `dev-essentials:engineering-discipline` Rule 3).
