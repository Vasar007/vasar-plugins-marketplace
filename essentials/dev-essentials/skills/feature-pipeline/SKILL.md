---
name: feature-pipeline
description: Use when the user asks to implement a tracked task, run the feature pipeline, develop a feature end-to-end, start the task pipeline for TASK-123, run feature-pipeline, or implement TASK-123. Orchestrates a full implementation-first development pipeline for a task provider in an isolated git worktree.
argument-hint: <task-id> [--dry-run] [--no-worktree] [--start-from=<stage>] [--skip=<stage>] [--model-override=<stage>:<model>]
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
| — | **Human Approve** | — | ✓ |
| 3 | Implementation | code changes | — |
| — | **Build Gate** | — | — |
| 4 | Test coverage | test files | — |
| 5 | Code simplifier | code changes | — |
| 6+7+8 | Docs + Code Review + Security Review (parallel) | docs, `{ARTIFACTS_DIR}/{task-id}/review.md`, `{ARTIFACTS_DIR}/{task-id}/security-review.md` | — |
| — | **Human Approve** | — | ✓ |
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

Stage names: `requirements`, `spec`, `implementation`, `test-coverage`,
`simplifier`, `docs`, `review`, `security-review`, `finalization`

Valid model values: `opus`, `sonnet`, `haiku`

## Pipeline Discipline

These three safeguards apply to every stage. Subagents dispatched by this pipeline MUST honour them.

**Safeguard 1 — Verify Claude Code primitive claims against the system prompt.**
Before asserting how any Claude Code primitive works (Skill tool dispatch, Agent tool subagent types, settings merge order, MCP tool prefixing, plugin loading, slash-command routing, memory system semantics), check the current system prompt — do not pattern-match from training data. If uncertain, say "I'm not sure; let me check" rather than stating a categorical rule. The system prompt is the session-scoped source of truth and changes between harness versions. See `dev-essentials:engineering-discipline` for the broader verify-before-asserting principle.

**Safeguard 2 — Verify before proposing confident fixes for schema/manifest/config errors.**
At any stage — implementation, test coverage, or review — whenever a schema error, manifest validation failure, or library API mismatch is encountered or diagnosed, verify against a primary source (official docs, known-working example) BEFORE proposing a fix. Frame unverified theories as theories ("this might be…"), not fixes. Checking a known-working plugin takes 30 seconds and prevents rolling back wrong edits. See `dev-essentials:subagent-orchestration` for briefing-quality expectations.

**Safeguard 3 — Scope and host check before recommending MCP restart.**
When a task-provider MCP server fails, perform TWO checks before investigating install state or recommending restart: (a) is the failure session-local or global — does it fail in other concurrent Claude sessions? (b) what is hosting Claude Code — some terminals isolate MCP child processes. If the host may be isolating subprocesses, suggest switching to a plain OS terminal (cmd / pwsh / Windows Terminal) rather than restarting in place.

## Plugin Dependencies

Stages 5 (Code Simplifier) and 7 (Code Review) delegate to subagents provided
by external plugins. The pipeline will fail at those stages if the plugins are
not installed in the consuming environment.

| Stage | Required subagent | Provided by plugin |
| --- | --- | --- |
| 5 — Code Simplifier | `code-simplifier:code-simplifier` | `code-simplifier` |
| 7 — Code Review | `feature-dev:code-reviewer` | `feature-dev` |

Stages 1, 2, 3, 4, 6, 8, 9 use the built-in `general-purpose` agent and have
no external dependencies.

Install both plugins before running the pipeline. If either is missing,
either install it or override the stage with `--skip=simplifier` /
`--skip=review` (at the cost of that stage's output).

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

After resolution, the master agent prepends the resolved context to every stage
prompt before performing placeholder substitution. See **Context Injection**
under Shared Placeholder Vocabulary for the full XML wrapper format, including
the `<task-context>` block that carries per-task data alongside the
project-context block.

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

> **MCP failure — scope and host first (Safeguard 3):** if the MCP server appears unavailable, check (a) whether it fails in other Claude sessions too, and (b) which terminal/IDE is hosting Claude Code. Session-local failures and sandboxed-terminal isolation are the two most common causes; if the host may be isolating subprocesses, suggest switching to a plain OS terminal (cmd / pwsh / Windows Terminal) rather than restarting in place.

## Shared Placeholder Vocabulary

The master agent substitutes only 3 structural placeholders into stage prompts
after context injection:

- `{TASK_ID}` — used in file paths across all stage prompts
- `{WORKTREE_PATH}` — absolute path to the project root (worktree path, or
  current working directory when `--no-worktree` is used)
- `{ARTIFACTS_DIR}` — repo-relative directory for pipeline artifacts (e.g.
  `tasks`, `Notes/Tasks`)

All other task-specific data is provided via two injected context files (see
**Context Injection** below), not as inline placeholders.

### Context Injection

Before performing placeholder substitution, the master agent prepends two
context blocks to every stage prompt:

```md
<project-context>
{resolved project context}
</project-context>

<task-context>
{contents of {ARTIFACTS_DIR}/<task-id>/task-context.md}
</task-context>

{original stage prompt with {TASK_ID}, {WORKTREE_PATH}, and {ARTIFACTS_DIR} substituted}
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

#### Review Feedback File

Review feedback for implementation re-entry is stored as a file, not a
placeholder:

- Path: `{ARTIFACTS_DIR}/<task-id>/review-feedback.md`
- Written by: master agent (before re-invoking implementation)
- Contains: the contents of `review.md` blocking issues
- The implementation stage prompt checks whether this file exists to determine
  if it is a re-entry run

### Default Model Assignment

| Stage | Default model | Rationale |
| --- | --- | --- |
| `requirements` | `opus` | Deep codebase exploration and analysis |
| `spec` | `opus` | Architectural thinking, spec design — critical for quality |
| `implementation` | `opus` | Code writing in large codebases — quality on first pass reduces costly retry loops |
| `test-coverage` | `sonnet` | Test writing — capable and cost-efficient |
| `simplifier` | `sonnet` | Mechanical simplification, well-defined task |
| `docs` | `haiku` | Documentation writing, deterministic output |
| `review` | `opus` | Critical review — must not miss issues |
| `security-review` | `opus` | Security analysis — must reason about multi-hop data flows in distributed services |
| `finalization` | `haiku` | Deterministic git and PR operations after discovery |

### Model Resolution

Before each stage launch, resolve the effective model:

1. Start with the default from the table above
2. If `--model-override` contains an entry for this stage, replace with the
   override value
3. Pass the resolved model to the `Agent` tool call via the `model` parameter

## Orchestration

### Step 0: Setup

1. Parse `$ARGUMENTS`:
  - Extract task ID (`$ARGUMENTS[0]`)
  - Parse flags: `--dry-run`, `--no-worktree`, `--start-from`, `--skip`,
     `--model-override`
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
11. Prepare context injection: take the resolved project context and
    `{ARTIFACTS_DIR}/<task-id>/task-context.md`, wrap each in its XML tags
    (`<project-context>` and `<task-context>`), and prepend both to every
    stage prompt before placeholder substitution
12. After `{TASK_ID}`, `{WORKTREE_PATH}`, and `{ARTIFACTS_DIR}` substitution,
    validate that no placeholder remains as a literal string in the composed
    prompt. If any is found, stop immediately and report which placeholder was
    missed and in which stage prompt
13. Read or initialize `{ARTIFACTS_DIR}/<task-id>/pipeline-state.json` inside
    the worktree (see **Checkpoint Protocol** below)
14. If `--dry-run`: announce the plan, provider details, branch name, worktree
    path, and the two planned task-comment checkpoints, then exit without
    running any stage

### Step 1: Requirements Analysis

Model: `opus` (override key: `requirements`)

Launch subagent with prompt from `stages/requirements.md`.
On completion: update checkpoint `completed: ["requirements"]`.

### Step 2: Spec & Test Plan

Model: `opus` (override key: `spec`)

Launch subagent with prompt from `stages/spec.md`.
On completion: update checkpoint.

### Human Approve #1 (after Spec)

Present to user:

- Summary of `{ARTIFACTS_DIR}/{task-id}/spec.md`
- Summary of `{ARTIFACTS_DIR}/{task-id}/test-plan.md`
- Ask: "Approve spec and proceed to implementation? (yes / edit feedback)"

If user provides feedback: re-run Spec stage with feedback injected.
If approved: proceed.

### Task Comment #1 (before Implementation)

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

Model: `opus` (override key: `implementation`)

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
Model: `haiku` (override key: `docs`)
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

Present to user:

- `{ARTIFACTS_DIR}/{task-id}/review.md` contents
- `{ARTIFACTS_DIR}/{task-id}/security-review.md` contents
- Git diff summary (files changed, lines added/removed)
- Ask: "Approve for finalization? (yes / request changes)"

> **Verify before fixing (Safeguard 2):** when diagnosing review findings — and before re-invoking Implementation to address them — verify each finding against a primary source (official docs, the schema, a known-working example), especially schema/manifest errors and library API claims. Frame uncertain diagnoses as theories ("this might be…"), not confirmed fixes, until verified.

If review has blocking issues AND user approves auto-fix:

  1. Re-invoke Implementation subagent with review feedback (up to 1 retry)
  2. Remove these stages from `completed` in `pipeline-state.json`:
     `test-coverage`, `simplifier`, `docs`, `review`, `security-review`,
     `finalization`
  3. Re-run Step 4 (Test Coverage)
  4. Re-run Step 5 (Code Simplifier)
  5. Re-run Steps 6 + 7 + 8 in parallel
  6. Return to Human Approve #2 with fresh review artifacts
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

Model: `haiku` (override key: `finalization`)

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

1. Archive task logs: copy `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/` to
   `~/.claude/task-logs/{TASK_ID}/`. Create `~/.claude/task-logs/` if it does
   not exist. If the target directory already exists, overwrite its contents.
2. **If \****`--no-worktree`**\*\*:** skip worktree removal (there is no worktree to
   remove). Announce completion with the branch name and archived logs path.
3. **Otherwise — worktree removal is GATED. Do NOT remove by default.**
   The worktree must remain on disk until the PR is merged. PR review feedback,
   automated review follow-ups, and build/test reproduction all require the
   branch working tree. Removing it early strands work with no build capability.

   **No-PR branch** — if `pipeline-state.json` has `"pr": null` (branch-only
   flow or PR creation was skipped), keep the worktree on disk unless the user
   explicitly asks to remove it (delegate to
   `dev-essentials:git-worktree-management`'s user-directed override path).
   Do NOT auto-remove a no-PR worktree.

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
   silently skip the check and proceed to worktree removal.

   Remove the worktree only if **either** condition is met:
   - The PR `state` is `closed` and `merged` is `true`.
   - The user explicitly asks to remove the worktree.

   > **Bulk-cleanup requests are out of scope for this skill.** If the user
   > asks to remove worktrees broadly, delegate immediately to
   > `dev-essentials:git-worktree-management` **Workflow D** and stop the
   > pipeline. Do not enumerate or touch any other worktrees.

   If neither condition is met: leave the worktree on disk and skip removal.

   When removal is allowed: run `git worktree remove .claude/worktrees/<branch-name>`,
   then verify with `git worktree list`. If removal fails with "Permission denied"
   (file locks), report it to the user — **never force-remove**.

   See `dev-essentials:git-worktree-management` (Lifecycle Rule section)
   for the canonical keep-until-merged rule.

4. Announce completion: print the final branch or PR outcome, state whether the
   worktree was removed or intentionally kept (and why), and note the archived
   logs path.

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
  "failed": null,
  "startedAt": "2026-03-01T11:00:00Z",
  "updatedAt": "2026-03-01T11:30:00Z"
}
```

All state files for a task are stored under `{ARTIFACTS_DIR}/{task-id}/`
(e.g. `{ARTIFACTS_DIR}/task-123/`). This allows multiple tasks to coexist in the same
worktree without conflicts.

### Rules

- Update `stage` and `completed` after every successful stage
- Update `taskComments` after every successful provider comment post
- On startup: if `pipeline-state.json` exists, resume from first non-completed
  stage
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
  missing, post Task Comment #1 before continuing
- If Step 9 will run and `taskComments.preFinalizationPostedAt` is missing, post
  Task Comment #2 before continuing

---

## State-Sharing Protocol

All inter-agent communication happens through files in `{ARTIFACTS_DIR}/{task-id}/`:

| File | Written by | Read by |
| --- | --- | --- |
| `{ARTIFACTS_DIR}/{task-id}/task-context.md` | Master agent (setup) | All stage agents (injected) |
| `{ARTIFACTS_DIR}/{task-id}/requirements.md` | Requirements agent | Spec agent |
| `{ARTIFACTS_DIR}/{task-id}/spec.md` | Spec agent | Implementation agent, Human |
| `{ARTIFACTS_DIR}/{task-id}/test-plan.md` | Spec agent | Test Coverage agent |
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
  `completed`, `taskComments`, `buildGate`, `pr`, `failed`, `startedAt`, `updatedAt`
- **Backwards compatibility:** when loading state files written before this skill version (no `pr`
  key), default to `pr: null`. Stage 9 will populate it on the next PR creation; Stage 10 treats
  `null` as the no-PR branch. On the next checkpoint write, persist `"pr": null` so subsequent
  runs see the updated schema. The `pr` key is still required on every WRITE — this fallback
  applies to READs only.
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
- [implementation.md](./stages/implementation.md) — Feature implementation
- [test-coverage.md](./stages/test-coverage.md) — Test coverage check
- [simplifier.md](./stages/simplifier.md) — Code simplification
- [docs.md](./stages/docs.md) — Documentation update
- [review.md](./stages/review.md) — Code review
- [security-review.md](./stages/security-review.md) — Security review
- [finalization.md](./stages/finalization.md) — Finalization
