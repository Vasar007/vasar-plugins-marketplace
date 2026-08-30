---
description: Research → plan (with a user sign-off gate) → implement → review-loop → report cycle for one task, worked end-to-end in a single session — no OpenSpec change required (unlike opsx-implement/feature-pipeline) and doesn't stop short of review (unlike implement)
argument-hint: <task description, plan file path, or issue reference> [--base=<branch>] [--branch-prefix=<prefix>] [--commit-mode=per-phase|single] [--rounds=N] [--context=<path>...] [--skip-research]
---
<!-- markdownlint-disable MD013 -->

# Research → Implement → Review-Loop → Report

A single end-to-end cycle for one task, requirement, or bug: research/plan
first, implement task by task, run an iterative multi-agent review loop on
what was implemented, then write a handoff report.

**Division of labour in this command family — read this before reaching for
a neighbour:**

- `dev-essentials:implement` — standalone "run the tasks already written in
  this plan file". No research phase, no review loop. Use it when the plan
  already exists and is trusted.
- `dev-essentials:research-implement-review-report` (this command) — the
  lighter-weight, non-OpenSpec cycle for **one** task: research/plan with a
  sign-off gate, implement, review-loop, report. Run it directly when there
  is no extra context to sweep first and no mandatory cleanup pass wanted —
  or let another command wrap it (see `implement-task` below), supplying an
  already-created worktree/branch, in which case Phase 0 below reduces to a
  verification step.
- `dev-essentials:implement-task` — a thin wrapper around this command for
  one task: adds an additional-context sweep (related PRs/issues, free-text
  notes) before research starts, and a mandatory `/simplify` pass after the
  review loop, landed as its own commit.
- `dev-essentials:implement-batch` — the batch shape: repeats this command's
  plan → implement → review cycle across N related tasks in one
  branch/worktree, sequentially, producing a one-commit-per-task stack plus
  one final cross-task review commit.
- `dev-essentials:feature-pipeline` — the full heavy pipeline for an OpenSpec
  change, with its own approval gates. Reach for it when the work genuinely
  needs the spec-tool machinery; this command is the non-spec-tool
  alternative for everything else.
- `dev-essentials:opsx-implement` — implements phases from an OpenSpec change
  that already exists, without owning research or review.

**Arguments**: $ARGUMENTS

- Format: `<task description, plan file path, or issue reference> [options]`
- Examples:
  - `Issue 123456 — wire the overwrite-existing-records flag through to the
    import pipeline`
  - `Notes/Plans/my-existing-plan.md` — skip straight to Phase 2 against an
    already-written plan (still runs Phase 1 briefly to load prior context,
    per `--context` resolution below)
  - `Fix the SingleOrDefault() 500 in InvoiceValidator --rounds=3`
  - `Create a worktree vvasilyev/tasks/123456-overwrite-existing-records from
    release/2.0, then follow this command's workflow.` — names the branch
    and base branch explicitly; skips branch-name derivation in Phase 0 below
    entirely.
- If no arguments, use the **AskUserQuestion** tool to ask what to work on.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | ask | Target/base branch to branch (or create a worktree) from. If neither this flag nor a base branch named in prose (e.g. "... from release/2.0") is present in $ARGUMENTS, use the **AskUserQuestion** tool to ask which branch to base this off — never assume `main`/`master`/`develop`. See Phase 0. |
| `--branch-prefix=<prefix>` | derive from context, else ask | Branch-name prefix for Phase 0's task-branch naming (`<branch-prefix>/tasks/<ID>-<short-description>`, etc.). Default: derive it from the invoking session's own established branch-naming convention if stated anywhere accessible (a project's own CLAUDE.md, or the user's global CLAUDE.md); if none is found, ask the user once per run before creating the branch. |
| `--commit-mode=<per-phase\|single>` | `per-phase` | `per-phase`: one commit after Phase 2 (Implement) completes, then Phase 3's own per-round commits. `single`: run every phase and every review round exactly the same way, but squash the whole run into **one commit at the end** — see "Commit cadence" below. |
| `--rounds=<N>` | `2` | Review-loop cycles. Forwarded to `dev-essentials:review-loop` as `--rounds`, overriding that skill's own default (`3`). |
| `--context=<path>` | auto | Prior research/handoff file to load instead of (or in addition to) fresh research. Same resolution as `dev-essentials:implement`'s `--context`. **Repeatable** — pass it more than once to load several files (e.g. a wrapper's generated context document plus the user's own); every path given is read, none displaces another. |
| `--skip-research` | off | Skip Phase 1 entirely (e.g., resuming a session where the plan already exists and is current). Phase 2 still loads `--context` if given. |

## Subagent dispatch

Every phase below dispatches subagents per
`dev-essentials:subagent-orchestration` — read that skill before running any
phase; it owns the dispatch rules and this command does not restate them.

Two additions specific to this command, not covered by that skill:

- **Model per stage**: research and planning (Phase 1) and reviewing
  (Phase 3) use Opus; implementing and fixing (Phase 2, Phase 3's fixer) use
  Sonnet — per the model matrix in the "Model selection" section of
  `dev-essentials:subagent-orchestration`.
- **Fable is exceptional-only and never dispatched silently on the agent's own
  initiative.** Even on a large or critical-path review where the model
  matrix marks Fable as eligible without the user having named it, ask first,
  every time — no exceptions.

## Progress tracking for the user

Keep a todo list so the user can see this run's status at a glance. Use
whichever task-tracking tool this session actually has loaded (`TodoWrite`,
or `TaskCreate`/`TaskUpdate`/`TaskList` — on newer models these are opt-in,
so don't assume one exists); if none is, fall back to the Phase 1 plan
file's own `- [ ]`/`- [x]` checkboxes plus a short status line at the top of
each response. Seed one entry per phase (Research & Plan, Implement, Review
loop, Report), flip each as it happens, and add per-task entries once Phase
2's task breakdown is known. This is for the user's visibility only — the
plan file stays the source of truth, and this list must never be used for
subagent coordination.

## Phases

### Phase 0 — Branch & worktree setup

0. **Pre-existing worktree/branch — verification only.** If the caller states
   that the worktree and branch already exist and supplies the branch name and
   the absolute worktree path (a wrapper such as
   `dev-essentials:implement-task` does exactly this), Phase 0 reduces to a
   **verification** step: confirm
   `git -C "<worktree path>" rev-parse --abbrev-ref HEAD` matches the expected
   branch. If it matches, skip steps 1-3 and run every later phase inside that
   worktree — do **not** re-derive a branch name and do **not** create a
   second worktree or branch. If the check does not match, STOP and ask the
   caller / user — do not create one to recover. If no pre-existing
   worktree/branch was supplied at all, continue with step 1.

1. Resolve the **base branch** — the branch this work branches off. Use it if
   named via `--base=<branch>` or in prose in $ARGUMENTS (e.g. "... from
   release/2.0"). Otherwise, use the **AskUserQuestion** tool to ask which
   branch to base off — never default to `main`/`master`/`develop` silently.
2. Resolve the **task branch name**. If $ARGUMENTS already names one
   explicitly (as in the worktree example under "Arguments" above), use it
   verbatim. Otherwise resolve `--branch-prefix=<prefix>` first (see the
   Options table above — derive from context, else ask), then build the
   branch name from that prefix and the issue reference in $ARGUMENTS,
   generalized across a GitHub issue's type or label:

   | Source | Branch name pattern | Example (`--branch-prefix=vvasilyev`) |
   | --- | --- | --- |
   | GitHub issue typed/labeled `task` | `<branch-prefix>/tasks/<ID>-<short-description>` | `vvasilyev/tasks/123456-add-invoice-pagination` |
   | GitHub issue typed/labeled `bug` | `<branch-prefix>/bugs/<ID>-<short-description>` | `vvasilyev/bugs/123456-fix-timeout` |
   | GitHub issue, any other type/label `<type>` | `<branch-prefix>/<type>s/<ID>-<short-description>` | `vvasilyev/features/123456-add-x` |
   | Research (no issue at all) | `<branch-prefix>/researches/<short-description>` | `vvasilyev/researches/investigate-y` |

   `<ID>` is the issue number parsed from $ARGUMENTS (e.g. `Issue 123456`
   or `#123456` → `123456`); the research pattern has no `<ID>` segment.
   `<short-description>` is a short kebab-case slug of the task description.
   If the issue's type or label can't be determined and it isn't a research
   task, ask the user rather than guessing which pattern applies.
3. If $ARGUMENTS asks for a worktree (e.g. "Create a worktree ... from ..."),
   create it per `dev-essentials:git-worktree-management` using the base
   branch from step 1 and the branch name from step 2. Otherwise, create/check
   out the branch normally per `dev-essentials:git-sync` conventions.
4. Run every subsequent phase inside that branch/worktree.

### Phase 1 — Research & Plan

Skipped entirely when `--skip-research` is set.

1. Resolve every `--context=<path>` given (the flag is repeatable — see the
   Options table), or derive one the way `dev-essentials:implement` does: from a
   plan-file argument, or from the auto-memory directory as a last fallback.
   Read them all in the orchestrating session before dispatching anything, and
   pass their findings verbatim into every research brief.
2. Dispatch one or more **Opus** research subagents to establish, grounded in
   the actual codebase (not assumption): what already exists, which files are
   involved, what patterns the surrounding code already uses, and what is
   genuinely unclear or open. Pass any user-supplied scope/context verbatim
   into the brief. Dispatch multiple research subagents concurrently when the
   task naturally splits (e.g. one on the production code path, one on
   existing test coverage, one on a permission/contract question).
3. Dispatch an **Opus** planning subagent (can be the same dispatch as step 2
   or a follow-up) to turn the research into a concrete implementation plan:
   ordered tasks/phases, the exact files each touches, and the decisions that
   need the user's sign-off before implementation starts (ambiguous
   behavior changes, public-contract changes, anything the current spec/plan
   doesn't already cover — per `dev-essentials:engineering-discipline`
   Rule 2, no unilateral critical decisions).
4. Save the plan to `Notes/Plans/<slug>-plan.md` (or the repo's own
   documented convention if `CLAUDE.md` specifies one) and **present it to
   the user for confirmation before Phase 2 starts** — this sign-off gate is
   the point of Phase 1. If the user flags open questions, resolve them here
   — do not carry ambiguity into Implement.

### Phase 2 — Implement

1. Load the plan from Phase 1 (or the plan-file argument if one was passed
   directly, or `--context` for a resumed session). `--context` accepts
   either shape documented in the Options table above, and both must actually
   work here, not just be accepted:
   - **Plan-shaped** (already contains a task checklist): use it as-is.
   - **Non-plan research/handoff file** (no task checklist): derive a task
     list from its content before proceeding, rather than choking on the
     missing checklist or refusing the file.
   - **With several `--context` paths** (this matters most when
     `--skip-research` is set, since Phase 1 is skipped entirely and Phase 2
     becomes the only consumer of `--context`): the plan-shaped one, if any,
     supplies the task list and the rest are read as research context; if
     none is plan-shaped, derive the task list from all of them combined.
2. For each task/phase in the plan, dispatch a **Sonnet** subagent to
   implement it, following the same brief discipline as
   `dev-essentials:implement` Step 4: follow existing patterns, ask rather
   than improvise, use the appropriate `.claude` skills for the change type
   (domain models, tests, controllers, configuration, etc.).
3. Mark each task complete in the plan file as it finishes (`- [ ]` → `- [x]`).
4. Build and test after each task (or after the whole batch, if tasks are
   small and tightly coupled) — never leave a red signal for the review
   loop to inherit.
5. See "Commit cadence" below for when this phase commits.

### Phase 3 — Review loop

Invoke `dev-essentials:review-loop` against what Phase 2 produced
(`target=branch` in the common case; `target=diff <range>` if only part of
the working tree should be reviewed) — do not reimplement any of its
mechanics (reviewer dispatch, triage, verify-then-fix, re-review) here; that
skill already owns them. Pass only what is this command's own — the skill's
shipped defaults cover everything else:

- `--rounds=<N>` from this command's `--rounds` (default `2`), overriding
  the skill's own default of `3`.
- Everything else uses `dev-essentials:review-loop`'s own defaults as
  shipped: `--reviewer=audit-team` (which falls back to `general-purpose`
  with a warning on a non-documentation target such as `target=branch` or
  `target=diff` — expected here, not an error), `--fixer=general-purpose`,
  `--skip=none` (nothing auto-deferred by severity label — every finding
  reaches merit-based triage instead), and a commit per cycle. Do not
  override any of these unless the user asks for a specific reviewer/fixer.
- Findings the user and the orchestrating session agree to genuinely defer
  are still recorded as deferred in Phase 4's report.
- See "Commit cadence" below for how the loop's own per-round commits
  interact with this command's commit mode.

### Phase 4 — Report

Write the handoff document the same way `dev-essentials:save-context` does —
in fact, follow that command's logic directly (`--plan=<path from Phase 1>`),
producing `Notes/Results/<slug>-report.md` (or the repo's own documented
convention, if one exists; or `-handoff-N.md` if this is a continuation of a
numbered session sequence the user is already keeping):

- **Overview** — what this run covered, branch, worktree, date.
- **What Was Done** — per phase: research findings, the plan, each
  implemented task, each review round's outcome.
- **Key Decisions** — table, with rationale, including every decision Phase 1
  or Phase 3 surfaced for user sign-off.
- **Issues Found** — anything discovered but out of scope for this run,
  candidate follow-up work items, and any process problems worth flagging to
  the user.
- **Key File Paths** — grouped by category (core, tests, config, docs).
- **What's Next** — remaining work, explicitly including whether the branch
  has been pushed/PR'd (default: no — pushing needs the user's explicit
  go-ahead, same as `review-loop`'s own guardrail).

Confirm to the user where the report was saved and give the same one-line
summary `save-context` gives, plus the final review-loop verdict
(`stop-clean` / `stop-max-rounds` / `stop-blocked`). This includes
`save-context`'s next-session continuation prompt (its Step 6) — carrying the
worktree's absolute path and branch name whenever this run used one.

## Commit cadence

### Per-phase mode (default)

- **After Phase 2 completes** (all tasks for this run implemented, built,
  tested green): one commit. If the plan has multiple independent tasks,
  one commit per task is also acceptable — mirror whichever granularity the
  plan's own structure suggests — but never leave Phase 2's output
  uncommitted going into Phase 3.
- **During Phase 3**: the review-loop skill commits once per round by
  default — do not suppress this in per-phase mode.
- Never push by default, at any commit, in either mode.

### Single-commit mode (`--commit-mode=single`)

- Before Phase 2 starts, record the current `HEAD` SHA.
- Run Phase 2 and Phase 3 exactly as described above — including
  review-loop's normal per-round commits. Do not try to suppress those via
  `--dry-run` or `--no-verify-fix`; both of those also skip the actual fix,
  which is not what this mode is for.
- After Phase 3 finishes, and **before** Phase 4's report is written, squash
  everything from this run into one commit:
  `git reset --soft <recorded-SHA>` followed by a single commit whose
  message summarizes the implement step and every review round's fixes
  (e.g. `Task X — <summary> (implement + N review rounds)`).
- **Squash-base safety stop**: if anything outside this run's own changes
  landed on `HEAD` in the meantime (e.g. an unrelated concurrent commit),
  **stop and ask the user** before soft-resetting — do not silently squash
  across someone else's commit. A caller running this mode on a branch other
  callers may also be committing to (e.g. a wrapper that dispatches this
  command mid-cycle on a shared PR branch) is responsible for guaranteeing
  nothing else commits between the recorded SHA and this squash — this
  command does not coordinate that on the caller's behalf.

## Guardrails

- **Do not improvise.** If a research finding, a plan ambiguity, or a review
  finding's right resolution isn't clear, ask the user — do not guess.
- **Own every red signal** raised during Phase 2 or Phase 3's build/test
  steps in this session — never wave one off as "pre-existing" without
  verifying it actually predates this run (per
  `dev-essentials:engineering-discipline`).
- **No unilateral critical decisions** — public-contract changes, new DI
  dependencies, test-assertion relaxations — that the plan from Phase 1
  didn't already authorize. Surface them for the user instead.
- **Never push without the user's explicit go-ahead each time.**
