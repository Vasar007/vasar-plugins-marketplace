---
name: feature-pipeline
description: Use when the user asks to implement a tracked task, run the feature pipeline, develop a feature end-to-end, start the task pipeline for TASK-123, run feature-pipeline, or implement TASK-123. Orchestrates a full implementation-first development pipeline for a task provider in an isolated git worktree.
argument-hint: <task-id> [--dry-run] [--no-worktree] [--start-from=<stage>] [--skip=<stage>] [--model-override=<stage>:<model>] [--commit-mode=<per-step|finalization>] [--interactive]
disable-model-invocation: true
---
# Feature Pipeline

Implement a tracked task end-to-end using an implementation-first multi-agent pipeline in
an isolated git worktree.

## Overview

The pipeline runs 9 specialized subagents in sequence, each in an isolated
context:

| # | Stage | Output file | Human gate |
| --- | --- | --- | --- |
| 1 | Requirements analysis | `{ARTIFACTS_DIR}/{task-id}/requirements.md` | — |
| 2 | Spec & test plan | `{ARTIFACTS_DIR}/{task-id}/spec.md`, `{ARTIFACTS_DIR}/{task-id}/test-plan.md` | — |
| 2b | Plan artifact (HTML) | `{ARTIFACTS_DIR}/{task-id}/{task-id}-implementation-plan.html` | — |
| — | **Human Approve** | — | ✓ with `--interactive` |
| 3 | Implementation | code changes | — |
| — | **Build Gate** | — | — |
| 4 | Test coverage | test files | — |
| 5 | Code simplifier | code changes | — |
| 6+7+8 | Docs + Code Review + Security Review (parallel) | docs, `{ARTIFACTS_DIR}/{task-id}/review.md`, `{ARTIFACTS_DIR}/{task-id}/security-review.md` | — |
| — | **Human Approve** | — | ✓ (posts, push, PR) |
| 9 | Finalization + PR | branch ready, PR if supported | — |

## Arguments

- `$ARGUMENTS[0]` — Task ID (e.g. `TASK-123`) — **required**
- `--dry-run` — Produce plan only, write no code
- `--no-worktree` — Skip worktree creation, work on the current branch in
  the current working directory
- `--start-from=<stage>` — Resume pipeline from a specific stage name
- `--skip=<stage>` — Skip a specific stage (comma-separated for multiple)
- `--model-override=<stage>:<model>` — Override the model for a specific stage
  (comma-separated for multiple, e.g.
  `--model-override=review:sonnet,spec:sonnet`)
- `--commit-mode=<per-step|finalization>` — Commit cadence for the run.
  `finalization` (default) keeps the current single-commit-at-Stage-9
  behavior; `per-step` commits incrementally as each stage's changes go
  green. See **Commit Cadence** below. Note: the sibling command
  `research-implement-review-report.md` has its own `--commit-mode` flag with
  different values (`<per-phase|single>`) and default — differs
  intentionally: this pipeline's unit is a numbered stage, not a phase.
- `--interactive` — stop at Human Approve #1, and ask before each fix round of Human
  Approve #2, as before. See **Autonomy**.

Stage names: `requirements`, `spec`, `plan-artifact`, `implementation`,
`test-coverage`, `simplifier`, `docs`, `review`, `security-review`,
`finalization`

Valid model values: `opus`, `sonnet`, `haiku`, `fable`. A user-typed
`--model-override=<stage>:fable` is self-authorizing — the user's explicit
choice outranks the matrix. If the master agent picks Fable on its **own**
initiative: with `--interactive`, ask the user first, every time. Without it,
keep the default model of the stage (see **Autonomy**). Both per the
"Model selection" section of `dev-essentials:subagent-orchestration`.

## Autonomy

By default, this workflow does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. This default approval covers the whole task, up to the merge.

- At a decision gate, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run approved without a stop.
- These stops stay in every mode: deletion of data, posts to outside systems (for example GitHub comments, reviews, and issues, or documentation pages), push, and pull request creation. The merge always stays with the user.
- An action that the user approved for this run needs no new stop. Two cases count as approval. The first is a flag such as `--push`, `--commit-push`, `auto-push`, or `autonomous`. The second is a step of this workflow that names the action as its default.
- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Ask the user about every other critical decision.
- If a rule says to ask before a Fable dispatch that neither the user nor the defaults of this workflow chose, do not ask. Use Opus, and name the step in the final report.
- With `--interactive`, every gate stops and waits for the user, as the gate text says.
- When this workflow runs another workflow and this run has `--interactive`, pass the flag on.

## Pipeline Discipline

These three safeguards apply to every stage. Subagents dispatched by this pipeline MUST honour them.

**Safeguard 1 — Verify Claude Code primitive claims against the system prompt.**
Before asserting how any Claude Code primitive works (Skill tool dispatch, Agent tool subagent types, settings merge order, MCP tool prefixing, plugin loading, slash-command routing, memory system semantics), check the current system prompt — do not pattern-match from training data. If uncertain, say "I'm not sure; let me check" rather than stating a categorical rule. The system prompt is the session-scoped source of truth and changes between harness versions. See `dev-essentials:engineering-discipline` for the broader verify-before-asserting principle.

**Safeguard 2 — Verify before proposing confident fixes for schema/manifest/config errors.**
At any stage — implementation, test coverage, or review — whenever a schema error, manifest validation failure, or library API mismatch is encountered or diagnosed, verify against a primary source (official docs, known-working example) BEFORE proposing a fix. Frame unverified theories as theories ("this might be…"), not fixes. Checking a known-working plugin (e.g., `feature-dev`) takes 30 seconds and prevents rolling back wrong edits. See `dev-essentials:subagent-orchestration` for briefing-quality expectations.

**Safeguard 3 — Scope and host check before recommending MCP restart.**
When a task-provider MCP server fails, perform TWO checks before investigating install state or recommending restart: (a) is the failure session-local or global — does it fail in other concurrent Claude sessions? (b) what is hosting Claude Code — Warp or other sandboxed terminals isolate MCP child processes. If the host may be isolating subprocesses, suggest switching to a plain OS terminal (cmd / pwsh / Windows Terminal) rather than restarting in place.

## Plugin Dependencies

Stages 5 (Code Simplifier) and 7 (Code Review) delegate to subagents provided
by external plugins. The pipeline will fail at those stages if the plugins are
not installed in the consuming environment.

| Stage | Required dependency | Provided by plugin |
| --- | --- | --- |
| 5 — Code Simplifier | `code-simplifier:code-simplifier` (subagent) | `code-simplifier` |
| 7 — Code Review | `feature-dev:code-reviewer` (subagent) | `feature-dev` |
| 2b — Plan Artifact | `dev-essentials:create-html-artifact` (skill) | `dev-essentials` (same plugin — always present) |

Stages 1, 2, 2b, 3, 4, 6, 8, 9 use the built-in `general-purpose` agent and
have no external dependencies. Stage 2b's dependency is bundled in this same
plugin, so it can never be "not installed" — the "will fail if the plugin is
not installed" caveat below applies only to Stages 5 and 7.

Install both external plugins (`code-simplifier`, `feature-dev`) before
running the pipeline. If either is missing, either install it or override
the stage with `--skip=simplifier` / `--skip=review` (at the cost of that
stage's output).

## Commit Cadence

Five stages can create a commit: **Implementation** (Stage 3 — including the
Human Approve #2 fix rounds, which re-invokes this same stage),
**Test Coverage** (4), **Code Simplifier** (5), **Docs** (6), and
**Finalization** (9). Every one of them (a) follows the resolved
`{COMMIT_MODE}` and (b) receives the injected `<commit-conventions>` block
defined below. Both facts are stated here once for all five stages and are
deliberately NOT restated at the individual stage-launch sections under
**Orchestration**. No other stage commits — Stage 2b (Plan Artifact) is
explicitly read-only with respect to git (see `stages/plan-artifact.md` Rules).

### Finalization-commit mode (default)

Current behavior, unchanged: every stage stages its own changes only
(`git add <explicit paths>`, never `-A`/`.`) and never commits. Stage 9
(Finalization) creates the single commit for the whole run, then pushes and
opens the PR.

### Per-step commit mode (`--commit-mode=per-step`)

The master agent MUST state the override explicitly in each stage subagent
prompt via `{COMMIT_MODE}` — do not assume a subagent infers it.

- **Stage 3 (Implementation)** — one commit per `spec.md` §4 execution-order
  step, once that step's build and tests are green (explicit
  `git add <path>`, never `-A`/`.`). Fix-iteration rounds within the same
  step each get their own commit once green.
- **Stage 4 (Test Coverage)** — one commit for the added/updated test files.
- **Stage 5 (Code Simplifier)** — one commit per file simplified, or one
  total commit if a single simplification spans multiple files.
- **Stage 6 (Docs)** — one commit for the doc update.
- **Human Approve #2 fix rounds** — granularity is authoritatively defined in
  `stages/implementation.md` Phase 4 (one commit per fixed finding); this
  file does not restate it.
- **Stage 9 (Finalization)** — pushes and opens the PR; it must NOT need to
  create a commit. If `git status` shows uncommitted or unstaged source
  changes at the start of Stage 9, STOP and report — do not commit them
  there.

Both modes: never push between commits — push only at Stage 9. Never commit
anything under `{ARTIFACTS_DIR}/`.

### Commit-Conventions Injection Block

This is the single source of the commit-message rules for the whole pipeline.
The master agent injects it as the `<commit-conventions>` context block into
each of the five commit-capable stage prompts listed at the top of this
section. Copy the fenced block below **verbatim** — do not paraphrase,
summarize, reorder, or trim its bullets. Exactly two things change on the way
in: the `{CADENCE_LINE}` token is replaced per the table below, and
`{ARTIFACTS_DIR}` is substituted like any other placeholder.

`{CADENCE_LINE}` — use exactly one, per the resolved `{COMMIT_MODE}`:

| `{COMMIT_MODE}` | Line to substitute for `{CADENCE_LINE}` |
| --- | --- |
| `finalization` | Commit cadence for this run: **finalization**. Only the Finalization stage creates a commit — one commit for the whole run. Every earlier stage stages its own changes with an explicit `git add <path>` (never `-A` or `.`) and does NOT commit. |
| `per-step` | Commit cadence for this run: **per-step**. Each stage commits its own changes as they go green, staging with an explicit `git add <path>` (never `-A` or `.`). The Finalization stage creates no commit — it expects a clean tree. Your stage's commit granularity is defined in your own stage instructions. |

Block body — inject verbatim:

```md
{CADENCE_LINE}

Commit-message rules — these apply to EVERY commit you create in this run.
Follow them exactly; do not invent your own format.

- **Subject** — ≤70 chars, describing WHAT changed, not HOW. Match the repo's
  existing commit-subject convention: infer it by running `git log --oneline`
  against the base branch named in the Project Context above.
- **Body** — optional; 1-2 lines on WHY, in production-engineering terms. If
  the repo's history shows no multi-line commit bodies, omit the body.
- **No pipeline-internal references** anywhere in the message: no
  `{ARTIFACTS_DIR}/...` paths, no artifact section anchors (e.g. `spec.md §4`),
  no review-finding IDs, no pipeline stage names. Per
  `dev-essentials:engineering-discipline` Rule 3, the message must read
  as production engineering history that still resolves six months from now.
- **Trailer** — end the message with the standard Claude `Co-Authored-By`
  trailer. Do NOT hardcode a model name or version — use the exact trailer
  string the harness gives you for the model actually making this commit.
- **NEVER `--no-verify`.** If a hook fails, fix the underlying issue.
- **NEVER amend.** If anything needs correcting after a commit exists, create
  a NEW commit.
- **Do not push from your stage** — pushing happens only in the Finalization
  stage (if you *are* Finalization, follow your own stage instructions for
  when to push).
- **Never commit anything under `{ARTIFACTS_DIR}/`.**
```

## Project Context Loading

Before any task lookup or worktree creation, the master agent MUST resolve a
project-context document describing this repo's task provider, commands, and
conventions. The pipeline uses a layered strategy — first hit wins:

1. **Explicit context file** (preferred, most complete):
   `<repo-root>/.claude/feature-pipeline-context.md`
2. **Repo CLAUDE.md** (fallback, auto-discovered): extract what it can from
   `<repo-root>/CLAUDE.md` — Project Overview → Repository, Build Commands →
   Commands, Architecture / General Working Rules → Key Conventions.
3. **Ask the user** for any required field that neither source provided,
   using the `AskUserQuestion` tool — one question per missing required field.

A starter file is shipped with this plugin at
`${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/project-context.template.md` —
copy it to `<repo-root>/.claude/feature-pipeline-context.md` and fill in the
placeholders for a one-time setup.

### Required Project Context Fields

These fields MUST be resolved (from file, CLAUDE.md, or user answers) before
Step 0 begins:

- **Task Provider** — provider name, MCP server prefix, project identifier
- **Worktree** — branch-name template and allowed variables (only when
  `--no-worktree` is NOT set)
- **Repository** — repo type (git), base branch, solution/root path
- **Commands** — build, test, lint, push, PR commands
- **Key Conventions** — project-specific rules the agents must follow

### Optional Fields (do not block the pipeline)

- **Guidance Files** — repo-relative paths to guidance docs (e.g. architecture
  overviews, domain reference docs)
- **Architecture Docs** — repo-relative paths to architecture docs
- **Testing Docs**
- **Artifacts Directory** — repo-relative path for pipeline artifacts (defaults
  to `tasks` if absent)

### Resolution Algorithm

```text
resolved := {}

if exists(<repo-root>/.claude/feature-pipeline-context.md):
    resolved := parse_sections(that file)

if any required field is still missing AND <repo-root>/CLAUDE.md exists:
    derive missing fields from CLAUDE.md sections:
      - Project Overview + Repository Structure  -> Repository
      - Build Commands / Running Tests            -> Commands
      - General Working Rules / Code Style /
        Conventions / Architecture                -> Key Conventions
    (log each derivation so the user can audit it)

for each required field still missing:
    ask user via AskUserQuestion
    store the answer in `resolved` (and, if the explicit context file
    exists, offer to append the answer to it at end of run)

if Task Provider still missing -> STOP the pipeline (cannot fetch the task)
```

### Project Context Injection

The resolved context is injected as the `<project-context>` block. It is one of
several blocks prepended to each stage prompt — see **Context Injection** under
**Shared Placeholder Vocabulary** for the complete, canonical block list,
ordering, and per-stage applicability. Do not restate the concatenation shape
here; that section owns it.

This replaces the previous approach of discovering ~15 repo conventions at
runtime and substituting ~25 placeholders. Project-specific values are now
readable text in the injected context, not placeholder targets.

## Provider Capability Contract

The project context identifies the task provider and MCP server prefix. The
master agent must inspect the MCP server tools matching that prefix and choose
methods that satisfy these capabilities:

- Fetch task details by ID
- Fetch task comments by ID if the provider supports comments
- Create task comments by ID
- Fetch task metadata needed to determine title, description, labels, priority,
  and branch metadata if available

If the MCP server cannot satisfy the required capabilities, stop immediately.

> **MCP failure — scope and host first (Safeguard 3):** if the MCP server appears unavailable, check (a) whether it fails in other Claude sessions too, and (b) which terminal/IDE is hosting Claude Code. Session-local failures and Warp/sandboxed-terminal isolation are the two most common causes; if the host may be isolating subprocesses, suggest switching to a plain OS terminal (cmd / pwsh / Windows Terminal) rather than restarting in place.

## Shared Placeholder Vocabulary

The master agent substitutes only 4 structural placeholders into stage prompts
after context injection:

- `{TASK_ID}` — used in file paths across all stage prompts
- `{WORKTREE_PATH}` — absolute path to the project root (worktree path, or
  current working directory when `--no-worktree` is used)
- `{ARTIFACTS_DIR}` — repo-relative directory for pipeline artifacts (e.g.
  `tasks`, `Notes/Tasks`)
- `{COMMIT_MODE}` — the resolved commit cadence for this run, literally
  `per-step` or `finalization` (see **Commit Cadence** above)

`{CADENCE_LINE}` also appears in the Commit-Conventions Injection Block; it is
resolved by table lookup, not substitution, and never reaches a stage prompt.

All other task-specific data is provided via the injected context blocks (see
**Context Injection** below), not as inline placeholders.

### Context Injection

Before performing placeholder substitution, the master agent prepends these
context blocks to every stage prompt. `<project-context>` and `<task-context>`
go to every stage; `<commit-conventions>` goes only to the five commit-capable
stages listed at the top of **Commit Cadence** (`implementation`,
`test-coverage`, `simplifier`, `docs`, `finalization`) and is omitted for all
others:

```md
<project-context>
{resolved project context}
</project-context>

<task-context>
{contents of {ARTIFACTS_DIR}/<task-id>/task-context.md}
</task-context>

<commit-conventions>
{verbatim block from **Commit Cadence** → **Commit-Conventions Injection
Block**, with its cadence line selected for the resolved {COMMIT_MODE} —
commit-capable stages only}
</commit-conventions>

{original stage prompt with {TASK_ID}, {WORKTREE_PATH}, {ARTIFACTS_DIR}, and {COMMIT_MODE} substituted}
```

#### Task Context File

The master agent writes `{ARTIFACTS_DIR}/<task-id>/task-context.md` once during Step 0
(Setup) after fetching task details from the provider. Structure:

```markdown
# Task Context

- **Task ID:** TASK-123
- **Provider Record ID:** 12345 (or "none")
- **Title:** <task title>
- **Priority:** <priority or "unknown">
- **Labels:** <JSON array or comma-separated, or "none">
- **URL:** <provider URL or "none">
- **Branch:** <resolved branch name>

## Description

<full task description / body / issue text>

## Attachments

<JSON array of {title, url} objects, or "none">

## Doc Candidates

<JSON array of repo-relative paths to files mentioning the task ID, or []>
```

Use `"none"` for values not available from the task provider. Doc candidates
should be populated by scanning the worktree for files mentioning the task ID.

This file is added to the State-Sharing Protocol table — written by the master
agent, read by all stage agents.

#### Commit Conventions Block

Unlike the other two blocks, `<commit-conventions>` is **not** backed by a file
under `{ARTIFACTS_DIR}/` — its content is a fixed section of this SKILL file
(**Commit Cadence** → **Commit-Conventions Injection Block**), which the master
agent already has in context. It therefore gets no row in the State-Sharing
Protocol table.

- Populated: once, after `{COMMIT_MODE}` is resolved in Step 0 (Setup) and
  before the first stage launch. Its content is identical for every stage that
  receives it in a given run.
- Recipients: the five commit-capable stages named at the top of
  **Commit Cadence**. Stages that cannot commit do not receive it.
- Copied verbatim; the only permitted transformations are the cadence-line
  selection and the normal `{ARTIFACTS_DIR}` substitution. A composed prompt
  whose block differs from the source in any other way is a defect — the whole
  point of the block is that stage subagents never see SKILL.md, so a
  paraphrase here silently becomes the rule.

#### Review Feedback File

Review feedback for implementation re-entry is stored as a file, not a
placeholder:

- Path: `{ARTIFACTS_DIR}/<task-id>/review-feedback.md`
- Written by: master agent (before re-invoking implementation)
- Contains: the contents of `review.md` blocking issues
- The implementation stage prompt checks whether this file exists to determine
  if it is a re-entry run

### Default Model Assignment

Per-stage defaults below are this pipeline's own tier choices, built on the
model matrix and rules in the "Model selection" section of
`dev-essentials:subagent-orchestration` — see that section for what each
model is for and for the Haiku-scope and Fable guardrails; it is not restated
here.

| Stage | Default model |
| --- | --- |
| `requirements` | `opus` |
| `spec` | `opus` |
| `plan-artifact` | `sonnet` |
| `implementation` | `sonnet` |
| `test-coverage` | `sonnet` |
| `simplifier` | `sonnet` |
| `docs` | `sonnet` |
| `review` | `opus` |
| `security-review` | `opus` |
| `finalization` | `sonnet` |

### Model Resolution

Before each stage launch, resolve the effective model:

1. Start with the default from the table above
2. If `--model-override` contains an entry for this stage, replace with the
   override value
3. Pass the resolved model to the `Agent` tool call via the `model` parameter

Once a stage's effective model is resolved, persist it to
`pipeline-state.json` under a `models` object (`{"<stage>": "<model>"}`) so a
later resume honours the same choice. On resume, resolve with this
precedence (highest first):

1. A `--model-override` entry for this stage passed on *this* invocation —
   it also overwrites the persisted entry for that stage
2. An entry already recorded for this stage in `models` (from a prior run)
3. The default from the table above

### Stage-Start SHA Recording

Immediately before launching any of the five commit-capable stages
(`implementation`, `test-coverage`, `simplifier`, `docs`, `finalization`),
record `git rev-parse HEAD` into `pipeline-state.json` under a
`stageStartSha` object (`{"<stage>": "<sha>"}`) — the same incremental-write
shape as `models` above: it starts as `{}` and gains one entry per stage as
that stage launches. This captures the branch tip at the moment the stage
began, so a later resume can tell whether HEAD moved while that stage was
still incomplete. See **Checkpoint Protocol** → **Rules** for how this is
used to guard against silently restarting a partially-executed stage.

## Orchestration

### Step 0: Setup

1. Parse `$ARGUMENTS`:
  - Extract task ID (`$ARGUMENTS[0]`)
  - Parse flags: `--dry-run`, `--no-worktree`, `--start-from`, `--skip`,
     `--model-override`, `--commit-mode`
2. Resolve the project context using the layered strategy from
   **Project Context Loading** above (explicit file → CLAUDE.md derivation →
   user questions). Validate that all required fields are present.
3. Inspect MCP server tools matching the prefix from project context and
   identify methods that satisfy the required provider capabilities
4. Fetch task details and comments through the MCP server
5. Resolve the branch name:
  - If task metadata exposes an explicit branch name, use it
  - Otherwise render the branch template from project context using the
     allowed variables
6. Resolve project root (`{WORKTREE_PATH}`):

   **If \****`--no-worktree`**\*\*:**
  - Set `{WORKTREE_PATH}` to the current working directory (repo root)
  - Use the current branch as-is — do NOT create or switch branches
  - Log: "Running in-place on branch `<current-branch>`"
  - Skip all worktree creation, branch fetching, and settings.local.json
     copying

   **Otherwise (default — create worktree):**
  - Worktree path: `.claude/worktrees/<branch-name>`
  - If the worktree already exists: skip creation, log "resuming existing
     worktree"
  - **If the worktree does not exist yet:** before delegating to
     `dev-essentials:git-worktree-management` **Workflow A**, announce
     the resolved settings to the user:

     > I will create a worktree with the following settings:
     >
     > - **Path:** `<repo-root>/.claude/worktrees/<branch-name>/`
     > - **Branch:** `<branch-name>` (new / existing local / existing remote)
     > - **Base:** `<base-branch-from-project-context>`
     >
     > Starting the pipeline authorises this worktree creation. Continuing…

     Then delegate to Workflow A **in pipeline mode**: pass the resolved path
     and branch explicitly and note that the user already approved by starting
     the pipeline, so Workflow A's Step 3 confirmation prompt is pre-satisfied
     and must not block. Workflow A handles the full bootstrap sequence:
     fetches the base branch, runs `git worktree add` (choosing the correct
     Case A/B/C depending on whether the branch is new, exists locally, or
     exists on remote only), unsets upstream tracking
     (`git branch --unset-upstream`), copies `.claude/settings.local.json`
     into the worktree, and creates `Notes/`.
     Do NOT replicate these steps inline — invoke Workflow A so the full
     bootstrap runs every time, including the two steps (`--unset-upstream`
     and `mkdir -p Notes/`) that are omitted when creation is done ad hoc.

   **After resolution (both modes):** every subsequent file operation and
   subagent prompt MUST reference `{WORKTREE_PATH}` as the project root.
7. If the project context defines a **Pre-build** command, run it inside the
   `{WORKTREE_PATH}` directory. If it fails, stop immediately — build will
   fail without it.
8. Scan `{WORKTREE_PATH}` for files mentioning the task ID (for doc
   candidates)
9. Resolve `{ARTIFACTS_DIR}`: use the `Artifacts Directory` value from the
   resolved project context if one was provided. If absent, default to `tasks`.
10. Write `{ARTIFACTS_DIR}/<task-id>/task-context.md` with all task metadata,
    branch name, and doc candidates (see **Context Injection** in Shared
    Placeholder Vocabulary above)
11. Read or initialize `{ARTIFACTS_DIR}/<task-id>/pipeline-state.json` inside
    the worktree (see **Checkpoint Protocol** below). On an existing state
    file (a resume), immediately after loading it, run the
    resume-interruption STOP check from **Checkpoint Protocol** → **Rules**
    — this is its firing point, and it runs before sub-step 12 below applies
    any `{COMMIT_MODE}` overwrite. Under `--dry-run`, report the finding
    instead of stopping (see that section for the full rule).
12. Resolve `{COMMIT_MODE}`: if `--commit-mode` was passed on this
    invocation, use it; otherwise use the value already recorded in
    `pipeline-state.json`'s `commitMode` field from a prior run; otherwise
    default to `finalization`. Same precedence and conflict handling as
    `--model-override` (see **Model Resolution**): a `--commit-mode` passed
    on a resume — even when a commit-capable stage already ran under the
    previously-persisted mode — also overwrites the persisted `commitMode`
    value, and the resume logs the change. **Exception:** if the newly
    resolved value is `finalization`, the persisted value was `per-step`,
    and at least one commit-capable stage is already `completed`, do NOT
    log-and-allow this overwrite — STOP instead, per the
    `per-step → finalization` STOP rule in **Checkpoint Protocol** →
    **Rules**. Under `--dry-run`, report the finding instead of stopping
    (see that section for the full rule). After evaluating this Exception
    (and finding it does not apply), record the resolved value in
    `commitMode` so a later resume uses it unless `--commit-mode` is passed
    again on that invocation.
13. Prepare context injection: take the resolved project context,
    `{ARTIFACTS_DIR}/<task-id>/task-context.md`, and — for the five
    commit-capable stages only — the **Commit-Conventions Injection Block**
    from **Commit Cadence** with its cadence line selected for the resolved
    `{COMMIT_MODE}`. Wrap each in its XML tags (`<project-context>`,
    `<task-context>`, `<commit-conventions>`) and prepend them to each stage
    prompt before placeholder substitution (see **Context Injection** under
    **Shared Placeholder Vocabulary**).
14. After `{TASK_ID}`, `{WORKTREE_PATH}`, `{ARTIFACTS_DIR}`, and
    `{COMMIT_MODE}` substitution, validate that no placeholder remains as a
    literal string in the composed prompt. If any is found, stop immediately
    and report which placeholder was missed and in which stage prompt.
    `{CADENCE_LINE}` is resolved by table lookup rather than by placeholder
    substitution, so it must also be gone from the composed prompt — if it
    survives, the cadence line was never selected.
15. If `--dry-run`: announce the plan, provider details, branch name,
    worktree path, the resolved `{COMMIT_MODE}`, and the two planned
    task-comment checkpoints, then exit without running any stage

### Step 1: Requirements Analysis

Model: `opus` (override key: `requirements`)

Launch subagent with prompt from `stages/requirements.md`.
On completion: update checkpoint `completed: ["requirements"]`.

### Step 2: Spec & Test Plan

Model: `opus` (override key: `spec`)

Launch subagent with prompt from `stages/spec.md`.
On completion: update checkpoint.

### Step 2b: Plan Artifact (HTML)

Model: `sonnet` (override key: `plan-artifact`)
Agent type: `general-purpose`

Launch subagent with prompt from `stages/plan-artifact.md`.

**Failure mode is non-blocking.** If the subagent fails to produce the
artifact: retry once. If it still fails, log a warning and proceed to Human
Approve #1 without the artifact — a broken renderer must never block the
pipeline from reaching the human gate.

**Failure detection test:** failure = the subagent's final output has no
`ARTIFACT: <path>` line (see `stages/plan-artifact.md`'s final-line
contract), or the named file does not exist on disk.

On completion (success, retry-success, or give-up): update checkpoint —
`plan-artifact` is added to `completed` on all three outcomes, so a resume
does not re-attempt a known-broken render — and record `planArtifact` (see
**Checkpoint Protocol** → **Schema** below).

### Human Approve #1 (after Spec)

Without `--interactive`, report the paths of `spec.md`, `test-plan.md`, and the HTML artifact in one status line, and proceed. If `spec.md` lists open decisions without a resolution, ask them first. With `--interactive`:

Present to user:

- Summary of `{ARTIFACTS_DIR}/{task-id}/spec.md`
- Summary of `{ARTIFACTS_DIR}/{task-id}/test-plan.md`
- Path to the HTML implementation-plan artifact
  (`{ARTIFACTS_DIR}/{task-id}/{task-id}-implementation-plan.html`) for the
  user to open in a browser — or, if rendering failed or was skipped, a note
  saying so
- Ask: "Approve spec and proceed to implementation? (yes / edit feedback)"

> **Anti-bypass clause (with `--interactive`): this gate stands on its own.** A general
> session-level directive telling the agent to work without stopping for
> clarifying questions, or to "make the reasonable call and continue," does
> **NOT** authorize skipping this gate. Those directives resolve ambiguity
> (what would otherwise be a clarifying question); this gate is a consent
> checkpoint that exists specifically to capture explicit user approval —
> skipping it is not "the reasonable call," it is exactly the call the gate
> exists to prevent.
>
> **Counts as explicit gate-skip authorization** (only these, or clear
> equivalents, waive the gate — and only if typed by the user in this
> session): "approve all gates", "auto-approve the pipeline", "skip Human
> Approve #1/#2", "I trust you, run end-to-end".
>
> **Does NOT count** — the gate stays armed: "no clarifying questions", "make
> the reasonable call", a bare "continue"/"ok" carried over from unrelated
> context, or any synthesized/inferred authorization the agent talks itself
> into.
>
> **Worked cautionary example:** in a past run, a general "work without
> stopping for clarifying questions" session instruction was misread as
> authorization to bypass both approval gates; the pipeline ran straight
> through implementation and pushed a fix to a shared branch without review.
> That is the failure mode this clause exists to prevent — default to
> `AskUserQuestion` (or stop and wait) at every gate, never a paraphrase of
> "the user said to continue."

Without `--interactive`, the default approval of **Autonomy** applies. The failure in the example cannot happen again, because the push, the PR, and the task comments still wait for Human Approve #2.

If user provides feedback: re-run Spec stage with feedback injected.
If approved: proceed.

### Task Comment #1 (before Implementation)

Without `--interactive`, do not post this comment now. Write it to `{ARTIFACTS_DIR}/{task-id}/task-comment-1.md`. Post it at Human Approve #2, after the yes of the user and before Task Comment #2. Then write "implementation started" in the past tense. With `--interactive`, post it now, because the approval at Human Approve #1 covers it.

Before launching Step 3, post an English comment to the task through the
configured task-provider MCP server.

The comment should be concise and summarize:

- the task objective in plain English
- the approved implementation approach from `spec.md`
- the planned test strategy from `test-plan.md`
- key constraints, risks, or migrations called out by the analysis
- that implementation is starting now
- a footer line: "This comment was generated by Claude Code"

If the task provider supports Markdown comments, prefer short headings and flat
bullets. Otherwise post the same content as plain text.

If comment creation fails, stop immediately.
On success, record the timestamp and provider comment ID if available in
`pipeline-state.json`.

### Step 3: Implementation

Model: `sonnet` (override key: `implementation`)

Launch subagent with prompt from `stages/implementation.md`.
On completion: update checkpoint.

### Build Gate (after Implementation)

The master agent runs the build command from Project Context directly — no
subagent needed.

1. Run the build command from Project Context (e.g. the `dotnet build ...` line under Commands)
2. If build **succeeds**: update checkpoint, proceed to Step 4
3. If build **fails**:
  - Extract the first 50 error lines from build output
  - Write them to `{ARTIFACTS_DIR}/<task-id>/review-feedback.md` with an instruction to
     fix compilation only — no new features, no refactoring
  - Re-invoke the Implementation subagent (it will detect the feedback file)
  - After the fix attempt, re-run the build command
  - If the build fails again after 2 total attempts: STOP the pipeline and
     report the build errors to the user. Do not proceed to test-coverage with
     broken code
4. Record the build gate result (pass, pass-after-retry, or fail) in
   `pipeline-state.json` under a `buildGate` key

This gate prevents the test-coverage agent from wasting its entire budget on
compilation errors.

### Step 4: Test Coverage

Model: `sonnet` (override key: `test-coverage`)

Launch subagent with prompt from `stages/test-coverage.md`.
On completion: update checkpoint.

### Step 5: Code Simplifier

Model: `sonnet` (override key: `simplifier`)
Agent type: `code-simplifier:code-simplifier` (plugin dependency)

No skill injection needed — the plugin agent has built-in simplification logic.
Launch subagent with prompt from `stages/simplifier.md` (pipeline adapter only).
On completion: update checkpoint.

### Steps 6 + 7 + 8: Docs Update, Code Review & Security Review (parallel)

All three stages only read implementation code — launch in parallel:

**Stage 6 — Docs Update:**
Model: `sonnet` (override key: `docs`)
Agent type: `general-purpose`
Launch subagent with prompt from `stages/docs.md`.

**Stage 7 — Code Review:**
Model: `opus` (override key: `review`)
Agent type: `feature-dev:code-reviewer` (plugin dependency)
No skill injection needed — the plugin agent has built-in review logic.
Launch subagent with prompt from `stages/review.md` (pipeline adapter only).

**Stage 8 — Security Review:**
Model: `opus` (override key: `security-review`)
Agent type: `general-purpose`
No skill injection needed — prompt is self-contained with comprehensive
security methodology.
Launch subagent with prompt from `stages/security-review.md`.

Wait for all three to complete, then update checkpoint.

### Human Approve #2 (after Review)

This gate stops in every mode, because it approves the posts to the task provider, the push, and the PR of Stage 9. Without `--interactive`, and with blocking issues in the review, run one automatic fix round (the numbered steps below) before you show this gate. If the review still has blocking issues after that round, show this gate with the open blocking issues. If the user asks for a fix round (request changes), start one.

Present to user:

- `{ARTIFACTS_DIR}/{task-id}/review.md` contents
- `{ARTIFACTS_DIR}/{task-id}/security-review.md` contents
- Git diff summary (files changed, lines added/removed)
- Ask: "Approve finalization (task comments, push, PR)? (yes / request changes)"

> **Anti-bypass clause — same anti-bypass clause as Human Approve #1 above
> applies here.** See that section for the full phrase lists (what counts as
> explicit gate-skip authorization, what does not) and the worked cautionary
> example — this gate carries the identical protection, just not restated in
> full.
>
> **Verify before fixing (Safeguard 2):** when diagnosing review findings — and before re-invoking Implementation to address them — verify each finding against a primary source (official docs, the schema, a known-working example), especially schema/manifest errors and library API claims. Frame uncertain diagnoses as theories ("this might be…"), not confirmed fixes, until verified.

If the review has blocking issues, run a fix round in one of these cases:

- The run has no `--interactive`, and `autoFixRound` in `pipeline-state.json` is not `true`.
- The user asks for a fix round (request changes).

Fix round steps:

  1. Re-invoke Implementation subagent with review feedback (up to 1 retry)
  2. Remove these stages from `completed` in `pipeline-state.json`:
     `test-coverage`, `simplifier`, `docs`, `review`, `security-review`,
     `finalization`. In the same write, set `"autoFixRound": true` in
     `pipeline-state.json`. A missing key means `false`.
  3. Re-run Step 4 (Test Coverage)
  4. Re-run Step 5 (Code Simplifier)
  5. Re-run Steps 6 + 7 + 8 in parallel
  6. Return to Human Approve #2 with fresh review artifacts. Show the gate, even if blocking issues remain.
If approved: proceed.

### Task Comment #2 (before Finalization)

Before launching Step 9, post a second English comment to the task through the
configured task-provider MCP server.

The comment should be concise and summarize:

- what was implemented
- tests added or updated, plus the latest verification status
- documentation updates, if any
- code review and security review outcomes
- that the task is moving into finalization next
- a footer line: "This comment was generated by Claude Code"

If the task provider supports Markdown comments, prefer short headings and flat
bullets. Otherwise post the same content as plain text.

If comment creation fails, stop immediately.
On success, record the timestamp and provider comment ID if available in
`pipeline-state.json`.

### Step 9: Finalization + PR

Model: `sonnet` (override key: `finalization`)

Launch subagent with prompt from `stages/finalization.md`.
On completion: update checkpoint and report the resulting branch or PR status.

If the finalization subagent created a PR, persist its metadata in
`pipeline-state.json` under the `pr` key before Step 10 runs:

```json
"pr": {
  "number": 42,
  "url": "https://github.com/<owner>/<repo>/pull/42",
  "owner": "<owner>",
  "repo": "<repo>"
}
```

If no PR was created (branch-only flow or PR command unavailable), leave `pr`
as `null` in `pipeline-state.json`. Step 10 reads this field to decide whether
a GitHub PR status lookup is needed.

### Step 10: Cleanup

After the finalization result is confirmed:

1. **Determine PR review/merge status** (shared by both the archive step and
   the worktree-removal step below, so the GitHub PR lookup only happens
   once).

   **No-PR branch** — if `pipeline-state.json` has `"pr": null` (branch-only
   flow or PR creation was skipped), skip the PR lookup entirely — there is
   no PR to wait on.

   **PR branch** — re-fetch the PR status from GitHub using the `pr` fields
   recorded in `pipeline-state.json` (see `dev-essentials:github-mcp-conventions`
   Rules 1–2):

   ```
   mcp__plugin_github_github__pull_request_read(
       owner=<pr.owner>,
       repo=<pr.repo>,
       pullRequestNumber=<pr.number>
   )
   ```

   **If the GitHub MCP call fails** (MCP not loaded, network error,
   authentication timeout): STOP and ask the user — "GitHub PR lookup failed;
   should I proceed with cleanup based on the cached state, or wait?" Do NOT
   silently skip the check and proceed to archiving or worktree removal.

   **PR-branch eligibility test (shared by step 2 and step 4 below, when a
   PR exists):** an action (archiving in step 2, worktree removal in step 4)
   is eligible to run if **either** (a) the PR `state` is `closed` and
   `merged` is `true`, **or** (b) the user explicitly asks for that specific
   action now (e.g., "archive the task logs now", "go ahead and archive",
   "archive it anyway" for step 2; "remove the worktree" for step 4 — or an
   equivalent explicit instruction). Each step below just says
   "PR-branch-eligible" and substitutes its own action. This test does not
   cover the no-PR case — each step states its own no-PR handling separately,
   because that handling differs between archiving (auto-eligible with no
   PR) and worktree removal (never auto-eligible with no PR — see step 4).

2. **Archive task logs is GATED — do NOT archive by default right after the
   PR opens.** The task artifacts (`spec.md`, `review.md`, the HTML
   implementation-plan artifact, `pipeline-state.json`, ...) are still live
   working documents while the PR is under review —
   archiving mid-review is premature, and the worktree copy is the one that
   matters during review iterations. This is the same underlying principle
   as the keep-the-worktree-until-merged rule below: don't finalize
   artifacts for work that isn't actually done yet.

   Archive `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/` to
   `~/.claude/task-logs/{TASK_ID}/` (create `~/.claude/task-logs/` if it does
   not exist; if the target directory already exists, overwrite its
   contents) only if there was no PR to begin with, or the PR-branch
   eligibility test above is met for archiving.

   Otherwise: leave the artifacts in place under
   `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/` and skip archiving — report
   that archiving is deferred pending PR review.

3. **If \****`--no-worktree`**\*\*:** skip worktree removal (there is no worktree to
   remove). Announce completion with the branch name and, per step 2, either
   the archived logs path or a note that archiving is deferred pending PR
   review.
4. **Otherwise — worktree removal is GATED. Do NOT remove by default.**
   The worktree must remain on disk until the PR is merged. PR review feedback,
   automated review follow-ups, and build/test reproduction all require the
   branch working tree. Removing it early strands work with no build capability.

   **No-PR branch** — keep the worktree on disk unless the user explicitly
   asks to remove it (delegate to `dev-essentials:git-worktree-management`'s
   user-directed override path). Do NOT auto-remove a no-PR worktree.

   **PR branch** — reuse the PR status determined in step 1 (no second
   GitHub lookup needed).

   Remove the worktree only if the PR-branch eligibility test from step 1 is
   met for worktree removal (e.g., "clean up the worktree", "remove the
   worktree", "you can drop the worktree now" satisfies its user-explicit-ask
   condition).

   **Worktree removal always runs the step 2 archive first if it hasn't
   already run**, regardless of which condition (PR-completed or explicit
   user ask) triggered the removal — removal deletes
   `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/` along with the worktree, so
   anything worth keeping must land in `~/.claude/task-logs/{TASK_ID}/`
   first, mirroring `dev-essentials:git-worktree-management` Workflow C's
   "archive anything worth keeping before removal" precedent.

   > **Bulk-cleanup requests are out of scope for this skill.** If the user
   > asks to remove worktrees broadly (e.g., "remove all worktrees", "clean up
   > all merged worktrees"), **do NOT attempt bulk cleanup here** — this skill
   > manages exactly one worktree for the current task, and `pipeline-state.json`
   > carries a `pr` object only for that task. Delegate immediately to
   > `dev-essentials:git-worktree-management` **Workflow D** and stop the
   > pipeline. Do not enumerate or touch any other worktrees.

   If the eligibility test above is not met: leave the worktree on disk and
   skip removal.

   When removal is allowed: remove via `{WORKTREE_PATH}` (the absolute path
   resolved in step 6), not a hardcoded relative path — `git worktree remove
   {WORKTREE_PATH}`, then verify with `git worktree list`. If removal fails
   with "Permission denied", do NOT assume an IDE file lock — work through
   `dev-essentials:git-worktree-management` Workflow C's ordered
   diagnosis (shell CWD parked in the worktree, then Windows long paths, then
   leaf-first walkup) before reporting to the user. **Never force-remove.**

   See `dev-essentials:git-worktree-management` (Lifecycle Rule section)
   for the canonical keep-until-merged rule.

5. Announce completion: print the final branch or PR outcome, state whether the
   worktree was removed or intentionally kept (and why), and state whether task
   logs were archived or left in place pending PR review.

---

## Checkpoint Protocol

The master agent maintains `{ARTIFACTS_DIR}/{task-id}/pipeline-state.json` throughout
execution.

### Schema

```json
{
  "taskId": "TASK-123",
  "worktree": "feature/task-123",
  "noWorktree": false,
  "stage": "implementation",
  "completed": ["requirements", "spec"],
  "taskComments": {
    "analysisPostedAt": null,
    "analysisCommentId": null,
    "preFinalizationPostedAt": null,
    "preFinalizationCommentId": null
  },
  "buildGate": {
    "result": null,
    "attempts": 0
  },
  "pr": null,
  "models": {},
  "stageStartSha": {},
  "planArtifact": null,
  "commitMode": "finalization",
  "failed": null,
  "startedAt": "2026-03-01T11:00:00Z",
  "updatedAt": "2026-03-01T11:30:00Z"
}
```

The `pr` field is `null` until Stage 9 completes. When a PR is created, it is
populated with `{ "number": <int>, "url": "<string>", "owner": "<string>",
"repo": "<string>" }`. When Stage 9 runs a branch-only flow (no PR created),
`pr` remains `null`. Stage 10 uses this field to decide whether a GitHub PR
status re-fetch is needed before the archive and worktree-removal gates.

The `models` field starts as `{}` and gains one entry per stage
(`"<stage>": "<model>"`) as each stage's effective model is resolved (see
**Model Resolution** above). It grows incrementally as stages launch, and a
resumed run reads it back to keep using the same models unless a fresh
`--model-override` overwrites a specific entry.

The `stageStartSha` field starts as `{}` and gains one entry per
commit-capable stage (`"<stage>": "<sha>"`) as that stage launches — the
`git rev-parse HEAD` recorded at that moment (see **Stage-Start SHA
Recording** above). It grows incrementally the same way `models` does, and
it is the sole input to the resume-interruption STOP check in **Rules**
below.

The `planArtifact` field is `null` until Stage 2b runs. It is then populated
with `{ "path": "<repo-relative path>", "status": "rendered" | "failed" |
"skipped" }` — `"rendered"` when the HTML artifact was written successfully
(after 0 or 1 retries), `"failed"` when both attempts failed, and
`"skipped"` when the stage itself was skipped (e.g. `--skip=plan-artifact`).

The `commitMode` field is `"finalization"` by default and set to `"per-step"`
when `--commit-mode=per-step` is resolved in Step 0. It is persisted on every
checkpoint write so a resumed run honours the original choice unless
`--commit-mode` is passed again on that invocation, or unless the
`per-step → finalization` STOP rule (**Checkpoint Protocol** → **Rules**)
applies (see **Commit Cadence**).

All state files for a task are stored under `{ARTIFACTS_DIR}/{task-id}/`
(e.g. `{ARTIFACTS_DIR}/task-123/`). This allows multiple tasks to coexist in the same
worktree without conflicts.

### Rules

- Update `stage` and `completed` after every successful stage
- Update `taskComments` after every successful provider comment post
- On startup: if `pipeline-state.json` exists, resume from first non-completed
  stage
- **On startup, before resuming any commit-capable stage, verify it wasn't
  left partially executed.** Checkpoints are stage-granular only —
  `completed` tracks whole-stage names, with no sub-stage/step-level
  progress. This check is mode-agnostic — it does not key on `{COMMIT_MODE}`
  at all, so it catches both a `per-step` stage interrupted after making
  some of its own commits AND a `finalization`-mode Stage 9 interrupted
  after other stages' commits already landed (HEAD moved either way): for
  every commit-capable stage (`implementation`, `test-coverage`,
  `simplifier`, `docs`, `finalization`) that is NOT in `completed`, compare
  `git rev-parse HEAD` against that stage's recorded `stageStartSha` entry.
  If they differ, STOP and report — do not silently restart that stage from
  scratch, which would risk duplicate or conflicting commits for units
  already committed, or a Stage 9 that wrongly assumes a clean tree.
  - **Ordering:** this check runs immediately on loading `pipeline-state.json`
    (Step 0, sub-step 11) and BEFORE `{COMMIT_MODE}` resolution (Step 0,
    sub-step 12) applies its "log and allow" overwrite. It depends only on
    `stageStartSha` and `completed`, never on `{COMMIT_MODE}`, so a resume
    cannot escape it by also passing a new `--commit-mode` value.
  - **`--dry-run` interaction:** report the finding as part of the announced
    plan but do NOT stop execution — a dry run never touches the branch, so
    there is nothing to protect.
  - **Sanctioned way past this STOP:** there are two real cases, and only
    one of them is resolved by `--start-from` alone.
    (a) **Discard the extra commits:** reset HEAD back to the stage's
    recorded `stageStartSha`, then resume with `--start-from=<stage>` naming
    the interrupted stage (or a later one) — this is exactly what that
    flag's checkpoint-resume-point override is for, and HEAD now matches the
    recorded SHA so the check passes cleanly.
    (b) **Keep the extra commits:** `--start-from` alone does NOT touch
    `stageStartSha` or `completed`, so the STOP will fire again on the very
    next invocation unless the user also manually updates that state first —
    either add the interrupted stage name to `completed` in
    `pipeline-state.json`, or bring that stage's `stageStartSha` current to
    the new HEAD — before resuming with `--start-from=<stage>`.
    Do not resume past this STOP any other way.
- **On startup, when `{COMMIT_MODE}` resolution (Step 0, sub-step 12) is
  about to flip the persisted mode from `per-step` to `finalization`, guard
  the one gap the `stageStartSha` check above cannot see.** That check
  compares `git rev-parse HEAD` against a stage's recorded `stageStartSha`,
  but finalization-mode stages only stage changes and never commit
  per-stage — HEAD never moves during them — so there is nothing to compare
  when the incoming mode is `finalization`. Left unguarded, a resume that
  flips `per-step → finalization` would keep the earlier `per-step` commits
  already on the branch and let the new finalization run add one more
  tail-end commit, breaking the "one commit for the whole run" promise
  **Commit Cadence** makes for finalization mode. If the resolved
  `{COMMIT_MODE}` is `finalization`, the persisted `commitMode` (before this
  resume's overwrite) was `per-step`, AND at least one commit-capable stage
  is already in `completed` (i.e., it may already have committed under the
  old `per-step` mode), STOP and report before overwriting `commitMode` —
  do not silently accept the new mode. The reverse transition
  (`finalization → per-step`) needs no separate guard here in the common
  case: when no commit-capable stage runs between the resume point and
  Stage 9, it is already caught by Stage 9's own STOP under **Commit
  Cadence** on any uncommitted/unstaged change found at the start of
  Stage 9. (Residual, lower-severity gap: if a commit-capable stage does
  run in between, its bare `git commit` sweeps up the earlier
  finalization-mode staged changes, leaving the tree clean by the time
  Stage 9 runs — Stage 9's check does not catch that case. No separate
  guard is added for it here.) Every other resume case —
  `per-step → per-step`, `finalization → finalization`,
  `finalization → per-step`, or `per-step → finalization` with no prior
  commit-capable stage completions yet — keeps the existing log-and-allow
  behavior in sub-step 12 unchanged.
  - **Ordering:** this check is evaluated after sub-step 12 reads the
    persisted `commitMode` value but strictly BEFORE sub-step 12 writes the
    newly resolved value back to `pipeline-state.json`. Nothing is written
    to `pipeline-state.json` when this STOP fires.
  - **`--dry-run` interaction:** report the finding as part of the
    announced plan but do NOT stop execution, same as the `stageStartSha`
    check above.
  - **Sanctioned way past this STOP:** there are two real routes.
    (a) Resume with `--commit-mode=per-step` to keep the original cadence
    and let the run continue committing per step — this requires no
    `pipeline-state.json` mutation.
    (b) Reset the branch to before the `per-step` commits and start a
    fresh `finalization`-mode run — this must be paired with removing the
    affected commit-capable stages from `completed` (and their
    `stageStartSha` entries) in `pipeline-state.json`, or simply deleting
    `pipeline-state.json` entirely for a genuinely fresh run. Resetting the
    branch without also clearing this state leaves `completed` and
    `commitMode` pointing at the discarded commits, so the STOP fires again
    on the next invocation, and if bypassed anyway, the pipeline would skip
    re-running the reset stages and produce an empty finalization commit.
    Do not resume past this STOP any other way.
- `--start-from=<stage>` overrides the checkpoint resume point
- `--skip=<stage>` removes a stage from the execution plan entirely
- Before launching any stage, verify that all input files it requires exist
  (see the State-Sharing Protocol table). If any are missing, stop immediately
  and report which files are absent. This is especially important when
  `--start-from` skips earlier stages that would normally produce those files
- If an earlier stage is re-run and can change code or docs, remove all
  downstream dependent stages from `completed` before resuming
- If `requirements` or `spec` is re-run, clear both task-comment checkpoints so
  fresh summaries are posted from the updated analysis
- If any code, test, docs, review, or security stage is re-run after the
  second task comment was posted, clear only the pre-finalization comment
  checkpoint so it is regenerated from fresh results
- If Step 3 or any later stage will run and `taskComments.analysisPostedAt` is
  missing, post Task Comment #1 before continuing (without `--interactive`,
  Human Approve #2 posts it instead)
- If Step 9 will run and `taskComments.preFinalizationPostedAt` is missing, post
  Task Comment #2 before continuing
- `models` is written on every stage launch, per the precedence order in
  **Model Resolution** above; a resume that re-passes a conflicting
  `--model-override` also logs the change
- `stageStartSha` is written immediately before launching any commit-capable
  stage, per **Stage-Start SHA Recording** above; it is the sole input to
  the resume-interruption STOP check earlier in this list
- If `spec` is re-run, also remove `plan-artifact` from `completed` so the
  HTML plan artifact re-renders from the updated spec

---

## State-Sharing Protocol

All inter-agent communication happens through files in `{ARTIFACTS_DIR}/{task-id}/`:

| File | Written by | Read by |
| --- | --- | --- |
| `{ARTIFACTS_DIR}/{task-id}/task-context.md` | Master agent (setup) | All stage agents (injected) |
| `{ARTIFACTS_DIR}/{task-id}/requirements.md` | Requirements agent | Spec agent |
| `{ARTIFACTS_DIR}/{task-id}/spec.md` | Spec agent | Implementation agent, Human |
| `{ARTIFACTS_DIR}/{task-id}/test-plan.md` | Spec agent | Test Coverage agent |
| `{ARTIFACTS_DIR}/{task-id}/{task-id}-implementation-plan.html` | Plan Artifact agent | Human |
| `{ARTIFACTS_DIR}/{task-id}/review.md` | Review agent | Human, Finalization agent |
| `{ARTIFACTS_DIR}/{task-id}/review-feedback.md` | Master agent (re-entry) | Implementation agent |
| `{ARTIFACTS_DIR}/{task-id}/security-review.md` | Security Review agent | Human |
| `{ARTIFACTS_DIR}/{task-id}/pipeline-state.json` | Master agent | Master agent |

Pass the relevant file paths explicitly in each subagent prompt.

### Output Validation

After each stage completes, the master agent MUST validate the output before
updating the checkpoint. This catches structural problems early — before
downstream agents consume malformed input.

**pipeline-state.json validation** — on every write and on startup resume:

- Parse as JSON; if invalid, stop immediately
- Verify required keys exist: `taskId`, `worktree`, `noWorktree`, `stage`,
  `completed`, `taskComments`, `buildGate`, `pr`, `models`, `stageStartSha`,
  `planArtifact`, `commitMode`, `failed`, `startedAt`, `updatedAt`
- **Backwards compatibility:** Any of `pr`, `models`, `stageStartSha`,
  `planArtifact`, `commitMode` missing from an old state file defaults to
  its documented zero-value on READ, and is persisted on the next WRITE:

  | Field | Zero-value default |
  | --- | --- |
  | `pr` | `null` |
  | `models` | `{}` |
  | `stageStartSha` | `{}` |
  | `planArtifact` | `null` |
  | `commitMode` | `"finalization"` |

  Each key is still required on every WRITE — this fallback applies to READs
  only. Stage 9 populates `pr` on the next PR creation; Stage 10 treats `null`
  as the no-PR branch.
- Verify `completed` is an array of known stage names
- Verify `stage` is a known stage name or null

**Markdown artifact validation** — after the stage that produces each file:

| File | Required headings |
| --- | --- |
| `requirements.md` | `## 1. Task Summary`, `## 2. Scope`, `## 3. Acceptance Criteria`, `## 4. Technical Constraints`, `## 5. Open Questions & Recommendations`, `## 6. Risks & Considerations` |
| `spec.md` | `## 1. Resolved Questions`, `## 2. Architecture Overview`, `## 3. Implementation Steps`, `## 4. Execution Order`, `## 6. Edge Cases & Error Handling` |
| `test-plan.md` | `## 1. Test Strategy Overview`, `## 2. Test Cases`, `## 3. Tests for Existing Code`, `## 4. Coverage Expectations` |
| `review.md` | `## Blocking Issues`, `## Warnings`, `## Suggestions`, `## Summary` |
| `security-review.md` | `## Blocking Issues`, `## Warnings`, `## Summary` |

Validation rules:

1. Read the file content after stage completion
2. Check that every required heading exists (case-insensitive match)
3. If any heading is missing: log the missing headings, re-invoke the same
   stage with feedback: "Your output is missing required sections: [list].
   Rewrite the file with all required sections."
4. Maximum 1 retry for structural validation. If it fails again, stop the
   pipeline and report the malformed output to the user
5. Optional headings (like `## 5. Database Migrations` in spec.md) are not
   validated — their absence is acceptable

## Portability Verification

Before claiming the pipeline is ready for use in a new repo:

1. Confirm that one of the context sources is resolvable:
   `<repo-root>/.claude/feature-pipeline-context.md` OR enough content in
   `<repo-root>/CLAUDE.md` to derive the required fields.
2. Confirm all required fields (see **Required Project Context Fields**) are
   present or answerable via `AskUserQuestion`.
3. Confirm the branch template uses only the allowed placeholders listed in
   the context source.
4. Confirm the MCP server matching the Task Provider prefix covers the
   required task-provider capabilities.
5. Confirm no stage prompt hardcodes project-specific paths or commands that
   should instead come from the resolved project context.
6. Confirm all placeholders referenced by stage prompts are documented here.

Useful static checks (run from the consumer repo root):

```bash
# Explicit context file (if present)
cat .claude/feature-pipeline-context.md

# Find any leaked project-specific tokens in the installed plugin's stage prompts
rg --no-heading --line-number '<repo-specific-token-1>|<repo-specific-token-2>|<repo-specific-command>' "$CLAUDE_PLUGIN_ROOT/skills/feature-pipeline/stages"

# List remaining placeholders in the SKILL file and stages
rg --no-heading --line-number '\{[A-Z0-9_]+\}' "$CLAUDE_PLUGIN_ROOT/skills/feature-pipeline"
```

## Stage Prompts

Detailed subagent prompts live in the `stages/` directory:

- [requirements.md](./stages/requirements.md) — Requirements analysis
- [spec.md](./stages/spec.md) — Spec & test plan creation
- [plan-artifact.md](./stages/plan-artifact.md) — HTML implementation-plan artifact
- [implementation.md](./stages/implementation.md) — Feature implementation
- [test-coverage.md](./stages/test-coverage.md) — Test coverage check
- [simplifier.md](./stages/simplifier.md) — Code simplification
- [docs.md](./stages/docs.md) — Documentation update
- [review.md](./stages/review.md) — Code review
- [security-review.md](./stages/security-review.md) — Security review
- [finalization.md](./stages/finalization.md) — Finalization
