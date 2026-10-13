---
name: gop-work
description: >
  Full GOP workflow — plan, implement, finalize. Use ONLY when the user explicitly
  states they want to work in GOP mode. Activates at the START of a task to drive
  the complete workflow: planning → implementation → commit → push (by default after a go-ahead).
---

# GOP Work

Full end-to-end workflow that plans, implements, builds, tests, validates, and finalizes a task.

## Autonomy

By default, this workflow does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. This default approval covers the whole task, up to the merge.

- At a decision gate, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run approved without a stop.
- These stops stay in every mode: deletion of data, posts to outside systems (for example GitHub comments, reviews, and issues, or documentation pages), push, and pull request creation. The merge always stays with the user.
- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Ask the user about every other critical decision.
- If a rule says to ask before a Fable dispatch that neither the user nor the defaults of this workflow chose, do not ask. Use Opus, and name the step in the final report.
- With `--interactive`, every gate stops and waits for the user, as the gate text says.
- When this workflow runs another workflow and this run has `--interactive`, pass the flag on.

| Option | Default | Description |
| --- | --- | --- |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |

To turn on `--interactive`, the user writes `--interactive` in the request.

## Execution flow

### Phase 0: Planning

Without `--interactive`: do not enter Plan Mode. Dispatch Explore and Plan agents in read-only mode. Write the plan to `<REPO_ROOT>/.claude/plans/<slug>.md`, with the same content as step 3 below. Report its path in one status line, and start Phase 1. Ask the user only the open decisions of the plan. With `--interactive`: run steps 2 to 6 below.

1. Detect the repository root:
   ```
   REPO_ROOT=$(git rev-parse --show-toplevel)
   ```
2. Call the **`EnterPlanMode`** tool to activate built-in Plan Mode. This restricts all operations to read-only and enables the structured planning workflow with a dedicated plan file.
3. **While in Plan Mode**, follow the built-in planning workflow:
   - Explore the codebase using Explore agents to understand relevant code, patterns, and architecture.
   - **Check available skills**: review the skill list in the system prompt. Identify every skill whose trigger description matches the task. Read each matching skill's SKILL.md (via Explore agents or Read tool) to understand its mandatory deliverables, completion checklist, and subagent delegations. Incorporate these requirements into the plan.
   - Design the implementation approach using Plan agents.
   - Write the plan to the plan file in `.claude/plans/` (path provided by Plan Mode). Include: context, files to modify, implementation steps, design decisions, risks/assumptions, **and mandatory artifacts from matching skills** (tests, subagent delegations, configuration changes).
   - Review the plan for alignment with the user's request.
4. After the plan is finalized, include the post-implementation pipeline overview in the plan or present it to the user:
   ```
   ## Post-implementation pipeline (automated)
   After implementation, the following stages run automatically:
   1. **Building** — builds affected projects, falls back to full solution
   2. **Testing** — runs relevant unit tests (skipped if no test projects found)
   3. **Validation** — reviews changes for completeness and quality
   4. **Commit & Push**: commits all changes. Without `--interactive`, it pushes after the go-ahead of the user. With `--interactive`, the plan approval covers the push.
   ```
5. Call **`ExitPlanMode`** to exit Plan Mode and return to normal operation. This signals readiness to proceed and prompts the user for plan approval.
6. Capture the plan file path for use in subsequent phases. If the user requests changes instead of approving, re-enter Plan Mode to revise.

### Phase 1: Implementation (main session)

6. Read `stages/01_implement.md` from the skill directory.
7. **Execute its instructions directly in the main session** (do NOT launch as a subagent — implementation may invoke skills that spawn their own subagents, and Claude Code does not allow nested subagents).
   Use the following context while executing:
   - `task_description`: the user's original request
   - `plan_file_path`: path to the plan file from Phase 0
   - `repo_root`: the detected repository root
   - `validator_proposals`: (optional) list of accepted proposals from a previous validation cycle — "None" on first run
8. After implementation is complete, record the `modified_files` list and `change_summary` for subsequent phases.

### Phase 2: Building

9. Launch a **gop-pipeline:gop-build** subagent, injecting:
    - `modified_files`: from Phase 1
    - `repo_root`: the detected repository root
10. Capture `build_status` (SUCCEEDED/FAILED) and `build_details` from output.
11. If `build_status` is FAILED, report to the user and **stop** — do not proceed to test.

### Phase 3: Testing (conditional)

12. Evaluate whether testing is relevant:
   - For each modified `.cs` file from Phase 1, walk up to the nearest `.csproj` and check whether a sibling/centralized test project exists (common patterns: `**/<AssemblyName>.Tests/`, `**/<AssemblyName>.Test/`, `tests/<AssemblyName>.Tests/`, `test/<AssemblyName>.Test/`). The full discovery logic lives in the `gop-test` subagent — this is just a quick existence probe to decide whether to launch it.
   - If NO test projects exist for ANY modified component, **skip this phase** and set `test_status = "NO_TESTS_FOUND"` (matching the value the test subagent would return for the same case — a single canonical no-tests status is used end-to-end).
13. If tests are relevant, launch a **gop-pipeline:gop-test** subagent, injecting:
    - `modified_files`: from Phase 1
    - `change_summary`: from Phase 1
    - `repo_root`: the detected repository root
14. Capture `test_status` (PASSED/FAILED/BUILD_FAILED/NO_TESTS_FOUND) and `test_details` from output.
15. If `test_status` is FAILED or BUILD_FAILED, report to the user and **stop** — do not proceed.

### Phase 4: Validation (parallel fan-out)

16. **Fan out to five validator subagents in parallel.** Send a single assistant message that contains five `Task` tool calls — one per specialist validator. Parallel dispatch is mandatory; serial dispatch defeats the purpose of the split (each validator is intentionally narrow; wall-clock = max of the five, not sum). Every subagent receives the **same** input block (prompt-injection only — never shared state):
    - `task_description`: the user's original request
    - `plan_file_path`: path to the plan file
    - `test_status`: from Phase 3 (or "NO_TESTS_FOUND")
    - `build_status`: from Phase 2
    - `repo_root`: the detected repository root
    - `modified_files`: from Phase 1
    - `change_summary`: from Phase 1
    - `deviations_from_plan`: from Phase 1
    - `unresolved_concerns`: from Phase 1

    Subagents launched:
    - `gop-pipeline:gop-validate-correctness` → emits `CORR-*` findings
    - `gop-pipeline:gop-validate-reuse` → emits `REUSE-*` findings
    - `gop-pipeline:gop-validate-security` → emits `SEC-*` findings
    - `gop-pipeline:gop-validate-compliance` → emits `COMP-*` findings
    - `gop-pipeline:gop-validate-performance` → emits `PERF-*` findings

17. **Collect the five per-agent reports.** Each validator emits a **rigid markdown report** (not JSON). The aggregator parses these reports deterministically. The contract every validator must follow:
    - Report-level fields: `## Validation status` (`APPROVED` | `APPROVED_WITH_WARNINGS` | `BLOCKED`), `## Domain` (one of Correctness, Reuse, Security, Compliance, Performance), `## Summary`, `## Issues` with `### Critical` / `### Warnings` / `### Info` subsections, `## Recommendation`.
    - Per-finding fields (mandatory for every CRITICAL and WARNING entry): `**[<PREFIX>-nn]** <title>`, `- Severity: CRITICAL | WARNING | INFO`, `- Confidence: nn%`, `- File: <path>:<line>`, `- Description: <text>`, `- Proposal: <text>`.
    - Optional per-domain extras: `- CWE/OWASP: ...` (security), `- Expected impact: ...` (performance), `- Requirement source: ...` (compliance).
    - Validators do NOT emit an `also_seen_by` field — that annotation is injected by the aggregator during rendering (step 18d) when it detects overlap across lenses.

18. **Aggregate into one unified validation report:**
    a. **Parse and merge.** Extract each finding record from the five markdown reports using the fields listed above. Build one combined list, preserving each finding's ID prefix (CORR-, REUSE-, SEC-, COMP-, PERF-) so its domain remains traceable.
    b. **Deduplicate.** Two findings collapse into one iff **both**: same `File: <path>:<line>` coordinate (or near-adjacent lines on the same logical element) AND semantically overlapping description. Keep the finding with the **higher Confidence %**; on the kept finding, inject an `also_seen_by: [<dropped-ID>, ...]` annotation (aggregator-generated, not a validator field) so reviewers see that multiple lenses agreed — evidence strength, not noise. When descriptions disagree meaningfully, keep both.
    c. **Compute overall `validation_status`:**
       - `BLOCKED` if any surviving finding has `Severity: CRITICAL`.
       - `APPROVED_WITH_WARNINGS` else if any surviving finding has `Severity: WARNING`.
       - `APPROVED` otherwise.
    d. **Render the unified report** grouped by severity first (CRITICAL → WARNING → INFO), then by domain (Correctness, Reuse, Security, Compliance, Performance) within each severity. Where a finding was kept during deduplication, print the `also_seen_by` annotation inline so the user can tell when two lenses concurred (e.g., `[SEC-02] ... [also seen by: REUSE-03]`).

19. **Route based on aggregated status and confidence (Human-in-the-Loop):**

    Without `--interactive`, decide yourself. For `APPROVED_WITH_WARNINGS`, accept every proposal with a confidence of 90% or more. For `BLOCKED`, accept every CRITICAL proposal, and every other proposal with a confidence of 90% or more. List the proposals that you did not accept in the final report. If you accepted a proposal, return to Phase 1 with the accepted proposals, and re-run Phases 2-4. Else proceed to Phase 5. A proposal that needs a critical decision outside the plan is a question for the user. With `--interactive`, route as below.

    **IF `validation_status` is APPROVED:**
    - Proceed directly to Phase 5. No user interaction needed.

    **IF `validation_status` is APPROVED_WITH_WARNINGS:**
    - Present the aggregated report to the user, showing all warnings with their confidence percentages, domain, proposals, and `also_seen_by` annotations where applicable.
    - Format as a numbered list the user can act on:
      ```
      Validators found warnings with improvement proposals. Review and decide:

      1. [CORR-01] <title> (Confidence: nn%)
         File: path/to/file.cs
         Proposal: <description>

      2. [SEC-02] <title> (Confidence: nn%) [also seen by: REUSE-03]
         File: ...
         Proposal: ...

      Options:
      a) Accept all proposals → re-run implementation with these fixes
      b) Accept specific proposals (e.g., "1, 3") → re-run with selected fixes only
      c) Reject all → proceed to commit as-is
      ```
    - If the user accepts any proposals: collect accepted proposals into `validator_proposals`, return to Phase 1 with this context, then re-run Phases 2–4.
    - If the user rejects all proposals: proceed to Phase 5.

    **IF `validation_status` is BLOCKED:**
    - Present the aggregated report to the user, grouping findings by confidence:
      - **High-confidence findings (≥ 90%):** present with strong recommendation to fix — these are very likely real issues.
      - **Lower-confidence findings (< 90%):** present with explicit note that the specialist is uncertain — these may be false positives.
    - Include all proposals (both criticals and warnings) in the same numbered-list format as above, with domain prefix and `also_seen_by` annotations preserved.
    - User options:
      - **Accept proposals** → collect accepted proposals into `validator_proposals`, return to Phase 1, re-run Phases 2–4
      - **Dismiss specific findings and proceed** → if user dismisses all CRITICALs, treat as override, proceed to Phase 5 with a warning note in the commit message
      - **Request manual fix** → user wants to fix it themselves outside the pipeline; stop and wait for user to signal readiness to resume

### Phase 5: Finalization

20. Launch a **gop-pipeline:gop-commit** subagent, and inject `repo_root` and `push`. Without `--interactive`, set `push: no`. Then ask the user for a go-ahead to push. After a yes, run the push yourself: `git -C <repo_root> push`. For a branch with no upstream, run `git -C <repo_root> push -u origin HEAD`. Never force-push. With `--interactive`, set `push: yes`, because the plan approval covers the push.
    - `repo_root`: the detected repository root
    - `push`: `yes` or `no`
21. Report the final result to the user: commit hash, push status, and any warnings from validation.

## Stages

| Order | Agent | Model | Phase | Purpose |
|-------|-------|-------|-------|---------|
| 0 | *(built-in Plan Mode with `--interactive`, else Explore and Plan agents)* | inherited | Planning | Create implementation plan |
| 1 | `stages/01_implement.md` (inline) | inherited | Implementation | Execute the plan |
| 2 | `gop-pipeline:gop-build` | sonnet | Building | Build affected projects |
| 3 | `gop-pipeline:gop-test` | sonnet | Testing | Run relevant tests (conditional) |
| 4a | `gop-pipeline:gop-validate-correctness` | opus | Validation (parallel) | Business logic, blast radius, breaking changes, logic bugs |
| 4b | `gop-pipeline:gop-validate-reuse` | sonnet | Validation (parallel) | Duplication, reuse opportunities, style consistency |
| 4c | `gop-pipeline:gop-validate-security` | opus | Validation (parallel) | Secrets, injection, authN/Z, crypto, supply chain |
| 4d | `gop-pipeline:gop-validate-compliance` | sonnet | Validation (parallel) | Plan coverage, skill-mandated artifacts, CLAUDE.md/REVIEW.md rules |
| 4e | `gop-pipeline:gop-validate-performance` | sonnet | Validation (parallel) | N+1, complexity, allocations, blocking I/O, caching |
| 5 | `gop-pipeline:gop-commit` | sonnet | Finalization | Commit and push changes |

## Rules

- Always start with the planning phase — never skip to implementation.
- Without `--interactive`, the plan is auto-approved (see "Autonomy"). With `--interactive`, never proceed to implementation without user approval of the plan.
- If the plan needs revision after partial implementation: without `--interactive`, revise the plan file, report the change, and ask only for a critical decision. With `--interactive`, pause and re-align with the user.
- Implementation (Phase 1) runs in the main session because it may invoke skills that spawn subagents — Claude Code does not support nested subagents.
- Phases 2-5 run as typed subagents (`gop-pipeline:gop-build`, `gop-pipeline:gop-test`, the five `gop-pipeline:gop-validate-*` specialists, `gop-pipeline:gop-commit`) with per-phase model selection and least-privilege tool scoping — pass data via prompt injection, not shared state.
- Phase 4 **must** dispatch the five validator subagents in a single assistant message containing five parallel `Task` tool calls. Serial dispatch is wrong — it erases the latency benefit of the split and causes cross-talk in the aggregator when findings arrive out of order. The aggregator only runs once all five reports are back.
- Subagents read files (plan, code) directly from the filesystem — pass paths, not content.
- If any phase fails (test, build), stop the pipeline and report to the user.
- With `--interactive`, only aggregated validation status of BLOCKED or APPROVED_WITH_WARNINGS triggers user interaction mid-pipeline. Without it, step 19 decides. Other failures are hard stops. The aggregated status is the worst-of the five specialists' statuses after dedup.
- When re-running Phase 1 with validator proposals, the full pipeline (Phases 1–4) re-runs, including all five validators in parallel. Do not skip build, test, or any validator after a proposal-driven re-implementation.
- Limit proposal re-run cycles to 2 iterations. If validation still finds CRITICAL issues after 2 re-runs, stop the pipeline and escalate to the user with the full history of aggregated findings.
- With `--interactive`, Plan Mode (Phase 0) uses the built-in `EnterPlanMode`/`ExitPlanMode` tools. In that case, do not launch a Plan subagent manually. Without it, Phase 0 uses Explore and Plan agents.
