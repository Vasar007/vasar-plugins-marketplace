---
description: Implement N related tasks in one branch/worktree — per task, plan → review-loop the plan → implement → commit → review-loop the code → squash to one commit — then one final cross-task review-loop squashed to a single commit. Never pushes.
argument-hint: <parent issue reference, or an explicit list of N tasks> [--base=<branch>] [--worktree=<branch-ref>] [--plan-dir=<path>] [--rounds=N] [--push] [--interactive]
---
<!-- markdownlint-disable MD013 -->

# Implement Batch (N tasks, N commits + at most 1 final-review commit)

**Division of labour in this command family — read this before reaching for
a neighbour:** `dev-essentials:implement` and `dev-essentials:opsx-implement`
work a single plan and stop at "implement + maybe commit".
`dev-essentials:research-implement-review-report` (RIRR) runs one task
end-to-end (research → plan → implement → review-loop → report).
`dev-essentials:implement-task` wraps RIRR for one task, adding a context
sweep and a mandatory simplify pass. **This command (`implement-batch`) is
the batch shape**: it repeats a per-task plan/review/implement/review/squash
cycle N times inside one shared branch/worktree, then runs one final
cross-task review pass over the combined result — with the commit topology
as the explicit deliverable. `dev-essentials:feature-pipeline` remains the
full heavy OpenSpec pipeline with its own approval gates, for when the work
genuinely needs that machinery instead.

Implement an arbitrary set of related tasks — typically the sub-issues of
one parent issue — inside a single branch or worktree, producing a clean
one-commit-per-task stack plus one final commit for the cross-task review
pass.

**Arguments**: $ARGUMENTS

- Format: `<parent issue reference, or an explicit list of N tasks> [options]`
- Examples (illustrative only — nothing here is hardcoded behavior):
  - `Issue 1469733 — implement all its sub-issues --base=release/2.0 --worktree=vvasilyev/tasks/1469733-custom-retention-enhancements`
  - `Tasks 1469734, 1469735, 1469736, 1469737 --base=release/2.0`
  - `Notes/Plans/custom-retention-plan.md — implement every task in this plan --base=release/2.0`
  - `1) add the retention option 2) wire it through the scheduler 3) cover it with tests --base=release/1.0 --worktree=vvasilyev/tasks/987654-retention`
- **N is whatever the user's input says** — parsed from the list, the plan
  file, or the parent's sub-issues. Never assume a count.
- If no arguments, use the **AskUserQuestion** tool to ask which tasks to
  implement.

**Options:**

| Flag | Default | Description |
| --- | --- | --- |
| `--base=<branch>` | from context, else ask | Use the base that this flag or the prose of $ARGUMENTS names (for example "... from release/2.0"). If neither names a base and `git ls-remote --heads origin` lists exactly one branch, use that branch, and say so. Else use the **AskUserQuestion** tool to ask. If the remote has more than one branch, never assume `main`/`master`/`develop`. See Step 0. |
| `--worktree=<branch-ref>` | ask or derive | Branch ref for the worktree all N tasks share. Use the value given here, or one named in prose in $ARGUMENTS, verbatim. Otherwise derive `<prefix>/<parent-type>s/<parent-ID>-<slug>` from the branch-naming convention documented in the repo's or the user's `CLAUDE.md`, and **ask once** if no convention is documented. |
| `--plan-dir=<path>` | `Notes/Plans/` | Directory (inside the worktree) for the per-task plan files. The repo's own documented plan location wins over this default. |
| `--rounds=<N>` | `2` | Review-loop cycles, forwarded to `dev-essentials:review-loop` as `--rounds` for every loop this command runs (plan loops, per-task code loops, and the final cross-task loop). |
| `--push` | off | Push the finished stack after the final report. **Off by default and off unless the user asks for it in this invocation** — the default contract is commit locally, report, and wait for the user's review. |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |

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
- When this workflow runs another workflow and this run has `--interactive`, pass the flag on, except to the Step 2 plan-review loops (see "Review-loop configuration").

## Subagent dispatch

Every step below dispatches subagents per
`dev-essentials:subagent-orchestration` — read that skill before starting.
It owns the dispatch rules (concurrent multi-`Agent`-call dispatch for
independent work), the no-`name`/no-teams rule, the delegate-external-MCP-
by-default rule, the absolute-worktree-path rule, and brief-quality
discipline; this command does not restate them.

Additions specific to this command:

- **Minimize main-session tokens; delegate essentially everything.** The
  orchestrating session resolves arguments, dispatches, runs the git
  bookkeeping (commit/squash/SHA recording), and talks to the user. It does not
  read source files, write code, or review diffs itself. Every subagent brief
  asks for a compact structured report — verdicts, `file:line` anchors,
  commands run and their results — never pasted diffs or file dumps.
- **Model per stage**: planning and reviewing use Opus; implementing and fixing
  use Sonnet; mechanical extraction (pulling sub-issues out of the tracker)
  may use Haiku — per the model matrix in the "Model selection" section of
  `dev-essentials:subagent-orchestration`.
- **Parallel where safe, sequential where not.** What makes concurrency unsafe
  here is not "writes a file" — it is **writing the same file, or running any
  git command that mutates the worktree, index, or history** (no
  `add`/`commit`/`checkout`/`reset`/branch operation; read-only inspection like
  `log`/`show`/`diff` is fine), in the one shared worktree. Two dispatches may
  run concurrently only when each writes to its own distinct path and neither
  runs a mutating git command.
  - **Step 2's planners qualify**: each writes exactly one
    `<--plan-dir>/<task-slug>-plan.md` — a distinct path per task — and mutates
    nothing via git, using read-only inspection only (e.g. to produce the
    `file:line` anchors the plan itself must include). Dispatch them
    foreground-parallel, and state the no-mutating-git-and-own-path-only
    constraint in every planner brief.
  - **Implementation does not qualify**: Step 3's implementers edit shared
    product and test files, and they commit. All N tasks share one worktree and
    one branch, so implement and review them **strictly one task at a time**.
    The same holds for the Step 2 plan-review loops (they commit) and the Step 4
    final loop.
- Fable is exceptional-only. Never dispatch it silently on the agent's own
  initiative. With `--interactive`, ask first, every time, also where the model
  matrix marks Fable as eligible. Without it, follow "Autonomy".
- **Every concrete, bounded dispatch is briefed to do the work itself, not to
  re-delegate** — planning one task's plan file, implementing one task, fixing
  one review finding — per `dev-essentials:subagent-orchestration`
  Rule 7 (no pass-through delegators).

## Progress tracking for the user

Seed a tracking list (`TodoWrite`, or `TaskCreate`/`TaskUpdate`/`TaskList` —
use whichever this session actually has; don't assume one exists) with one
entry per task plus one for the final review pass, and flip each as it happens.
Solo progress tracking for the user's visibility only — never as a coordination
channel between subagents (that stays banned per
`dev-essentials:subagent-orchestration`).

## Steps

### Step 0 — Resolve the batch

1. Determine the task list and therefore **N**:
   - An explicit list in $ARGUMENTS → use it verbatim, in the given order.
   - A plan file path → the plan's own task/phase list.
   - A parent issue reference → dispatch a subagent to enumerate its
     sub-issues from the tracker (per
     `dev-essentials:subagent-orchestration` Rule 4 and, for GitHub,
     `dev-essentials:github-mcp-conventions`). Then state the enumerated list
     and its count in one status line, and repeat it in the final report.
     Without `--interactive`, start working. With `--interactive`, **present
     the enumerated list to the user for confirmation** before you start. A
     derived list is where a silent miscount does the most damage. An explicitly
     supplied list needs no confirmation round-trip.
2. Resolve `--base` per the Options table.
3. Resolve the worktree branch ref per the Options table.
4. **If anything material is missing or ambiguous — which tasks, which branch,
   the worktree name, or the intended order/dependencies — use the
   AskUserQuestion tool now, before any work starts.** If nothing is unclear,
   start working.
5. Fix the implementation **order**: the user's stated order, else the
   dependency order the plan implies. State the order to the user in one line.

### Step 1 — Worktree setup

Create the worktree per `dev-essentials:git-worktree-management` (for a run
with `--interactive`, pass the flag on), branching
from the Step 0 base branch, and run its post-create bootstrap. Record its
**absolute path** — every write-capable dispatch from here on carries it
explicitly, per `dev-essentials:subagent-orchestration` Rule 6, and every
git call uses `git -C "<abs worktree path>"`.

Then record `BATCH_BASE_SHA = git -C "<worktree>" rev-parse HEAD`.

### Step 2 — Plan every task

Dispatch **Opus** planning subagents, foreground-parallel (one per task), each
writing `<--plan-dir>/<task-slug>-plan.md` inside the worktree. Each plan
carries: the task's scope, the files it will touch, the existing patterns it
must follow (with `file:line` anchors), its verification commands, and any
open decision (a critical decision that the task, the code, and the
documentation do not settle), per
`dev-essentials:engineering-discipline` Rule 2.

Then, for each plan, run `dev-essentials:review-loop` with
`target=spec <plan path>` and fix the plan per the loop's own verdicts. Use
the review-loop configuration in "Review-loop configuration" below.

Collect the open decisions from all N plans. Also collect every finding that a
plan-review fixer did not resolve with confidence. If the list is empty, start
Step 3 without a stop. Else ask the user all of them in one batch before Step 3.
Do not carry ambiguity into implementation. The plan-review loops run without a
triage stop, and this batch keeps them from swallowing an uncertain finding.

**Step 2 makes exactly one commit, and it lands before Step 3 begins.** The
parallel planner fan-out commits nothing. Then run the N plan-review loops one
at a time, letting each commit per cycle as the loop does by default. Once every
plan is reviewed and every open question is batched to the user, squash all of
Step 2's commits into one:

```bash
git -C "<worktree>" reset --soft <BATCH_BASE_SHA>
git -C "<worktree>" commit -m "Plans for <N> tasks (<N> plan reviews)"
```

The same squash-base safety stop as Step 3.6 applies. If Step 2 produced no
commits at all, there is nothing to squash — say so rather than manufacturing an
empty commit. This single commit is what `TASK_BASE_SHA[1] = BATCH_BASE_SHA`
(Step 3.1) absorbs into task 1's squash, so Step 2's output reaches the final
stack through one well-defined boundary rather than an indeterminate number of
loop commits.

### Step 3 — Per-task cycle (repeat for each of the N tasks, sequentially)

For task `i`:

1. **Record the task's base SHA**: for task 1, `TASK_BASE_SHA[1] = BATCH_BASE_SHA`
   from Step 1 — **not** a fresh `rev-parse`, so task 1's squash in Step 3.6
   also absorbs Step 2's single plans commit; for tasks 2..N,
   `TASK_BASE_SHA[i] = git -C "<worktree>" rev-parse HEAD`.
2. **Implement** — dispatch a **Sonnet** subagent with the absolute worktree
   path, the task's plan file path, the scope guard ("implement only this
   task"), the skills it must invoke for the change type (domain models, tests,
   controllers, configuration, …), and the build/test commands that prove it
   done. Mark plan items `- [ ]` → `- [x]` as they complete.
3. **Build and test** before committing — never hand a red signal to the review
   loop. Own every failure raised in this session (per
   `dev-essentials:engineering-discipline` Rule 1); for .NET repos follow
   `dev-essentials:dotnet-build-test` (`dotnet build` is authoritative;
   builds and tests run foreground).
4. **Commit** the task's implementation. Stage explicit paths — never
   `git add -A`/`git add .` — specifically this task's own source/test changes
   plus only this task's own plan file (`<plan-dir>/<this-task-slug>-plan.md`).
   Never stage another task's plan file, even if it happens to be dirty (e.g.
   already `- [x]`-updated from a later Step 2 pass, or pending for a future
   task).
5. **Review-loop the implementation** — `dev-essentials:review-loop` with
   `target=diff <TASK_BASE_SHA[i]>..HEAD`, committing once per review cycle (do
   not suppress the loop's own per-round commits).
6. **Squash this task's commits into one.** Only the commits belonging to *this*
   task — i.e. everything from `TASK_BASE_SHA[i]` to `HEAD`:

   ```bash
   git -C "<worktree>" reset --soft <TASK_BASE_SHA[i]>
   git -C "<worktree>" commit -m "<Issue ref> — <summary> (implement + <rounds> review rounds)"
   ```

   **Squash-base safety stop:** if anything that is not this task's own work
   landed between `TASK_BASE_SHA[i]` and `HEAD`, **STOP and ask the user**
   before soft-resetting — never squash across someone else's commit. For task
   1, Step 2's single plans commit falling inside this range is expected and is
   NOT an unexpected commit that should trigger this stop. If the review loop
   produced no commits at all, the task already has exactly one commit and the
   squash is a no-op — say so rather than manufacturing an empty commit.
7. Report a one-line status for the task and move to task `i+1`.

### Step 4 — Final cross-task review

1. Record `FINAL_BASE_SHA = git -C "<worktree>" rev-parse HEAD` (this is the tip
   of the N squashed task commits).
2. Run `dev-essentials:review-loop` once over the **combined** work —
   `target=diff <BATCH_BASE_SHA>..HEAD` — with the same configuration as every
   other loop in this command. This pass exists to catch what per-task reviews
   structurally cannot: cross-task inconsistency, duplicated abstractions,
   contradictory assumptions, and coverage gaps at the seams.
3. Commit once per review cycle, as the loop does by default.
4. **Squash only this final pass's own commits** — everything from
   `FINAL_BASE_SHA` to `HEAD`:

   ```bash
   git -C "<worktree>" reset --soft <FINAL_BASE_SHA>
   git -C "<worktree>" commit -m "Final review across <N> tasks — <summary of fixes>"
   ```

   The N per-task commits from Step 3 stay intact and untouched. The same
   squash-base safety stop applies. If the final loop produced no commits,
   there is nothing to squash — report the end state honestly as N commits with
   no final-review commit rather than inventing one.

### Step 5 — Report and stop

- **Do not push.** Stop here, report, and wait for the user's review. Push only
  if `--push` was explicitly passed in this invocation, and even then
  only after the report has been delivered.
- Verify and state the actual commit topology:
  `git -C "<worktree>" log --oneline <BATCH_BASE_SHA>..HEAD` — the expected end
  state is **N task commits + at most 1 final-review commit**. If the real
  topology differs, report the real one and explain why; never report the
  intended shape as if it were verified.
- Report, per task: what was implemented, which files, the review-loop verdict
  (`stop-clean` / `stop-max-rounds` / `stop-blocked`), and the squashed commit
  subject. For task 1 specifically, note explicitly that its commit also
  carries Step 2's cross-task plan-review fixes, not just task 1's own
  implementation.
- Report for the batch: the final review pass's verdict, the build/test state
  at `HEAD`, every decision that needed sign-off and how it was resolved, every gate that
  this run approved without a stop, and every finding deferred by agreement.
- Report the worktree's absolute path and the branch name, so the user can
  review it directly.

## Review-loop configuration

Every review loop this command runs — the Step 2 plan loops, the Step 3 per-task
code loops, and the Step 4 final loop — invokes `dev-essentials:review-loop`
and reimplements none of its mechanics (reviewer dispatch, triage,
verify-then-fix, re-review). The skill's own shipped defaults are what this
command wants — 2 cycles, one Opus reviewer, one Sonnet fixer with Opus
planning each fix, a commit per cycle, and nothing auto-deferred by severity
label — so there is no override block here. Only this is this command's own:

- `--rounds=<N>` from this command's `--rounds` (default `2`), forwarded to
  every loop this command runs.
- **`--interactive`**: without it, every loop runs without the Phase 4 triage
  stop. With it, pass `--interactive` to the Step 3 per-task loops and to the
  Step 4 final loop. Then the user sees those triages before the fixer proceeds.
  Do not pass it to the Step 2 plan-review loops. A finding that a plan-review
  fixer did not resolve with confidence still goes to the Step 2 batch.
- Commit after each review cycle in every loop — that cadence is what makes the
  per-task and final squashes well-defined.
- Findings deferred by agreement are recorded as deferred in Step 5's report.

## Guardrails

- **Never push by default.** Report and wait for the user's review; `--push`
  is the only opt-in, and only for the invocation that passes it.
- **N comes from the user's input.** Never assume a task count, and never
  silently drop or add a task.
- **One task per commit** in the final stack. Do not merge two tasks into one
  commit or split one task across two, unless the user asks. **One documented
  exception:** task 1's commit also carries Step 2's single plans commit, by
  design — `TASK_BASE_SHA[1] = BATCH_BASE_SHA` (Step 3.1) makes task 1's squash
  absorb it, which is why Step 5 requires that fact to be stated explicitly in
  the report. Step 3.2's "implement only this task" scope guard still binds task
  1's implementer — the absorption happens in the orchestrator's squash, never
  in a subagent's edits.
- **Squash only within the recorded boundaries** (`TASK_BASE_SHA[i]` for a task,
  `FINAL_BASE_SHA` for the final pass). Anything unexpected on `HEAD` is a
  STOP-and-ask, not a judgment call.
- **Implementation is sequential.** Never dispatch two subagents into the same
  worktree at once when either edits a shared file or runs a mutating git
  command. Step 2's planners are the one documented concurrent case — distinct
  plan-file paths each, and no mutating git — see "Parallel where safe,
  sequential where not".
- **Own every red signal** from any build or test run in this session — never
  wave one off as "pre-existing" without proving it predates the batch (per
  `dev-essentials:engineering-discipline`).
- **No unilateral critical decisions** — public-contract changes, new DI
  dependencies, test-assertion relaxations — beyond what the task's Step 2 plan
  authorized. Surface them to the user instead.
- **Do not improvise.** An unclear plan item, an ambiguous review finding, or a
  task that turns out bigger than its plan is an ask, not a guess.
- The per-task plan files are the source of truth for implementation — keep
  them updated as tasks complete.
