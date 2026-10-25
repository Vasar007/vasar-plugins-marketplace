---
name: gop-work
description: Full GOP (Git Operations Pipeline) workflow that plans, implements, builds, tests, reviews, commits, and pushes a task. Without --autonomous, the push waits for the approval of the user.
when_to_use: If the user explicitly asks for GOP mode at the start of a task, use it. Do not use it otherwise.
---

# GOP Work

Full end-to-end workflow that plans, implements, builds, tests, reviews with validator agents, and finalizes a task.

Dependency: the build and test phases (Phases 2 and 3) assume a .NET solution and the .NET SDK (`dotnet`) on `PATH`.

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
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If both checks below pass, you can delete such a branch with `git branch -D`. First, its pull request is merged. Find the pull request with `list_pull_requests`, with `head: "<owner>:<branch>"` and `state: "all"`. `<owner>` is the `owner` value of the call. The default state lists open pull requests only, and GitHub ignores a `head` value without the `<owner>:` prefix. Then read the pull request with `pull_request_read` (`method: "get"`), and make sure that `merged` is `true`. Use the GitHub MCP tools, not the `gh` CLI, as `dev-essentials:github-mcp-conventions` requires. Second, the local tip of the branch (`git rev-parse <branch>`) equals the head SHA of that merged pull request. If either check fails, or the run cannot read the state of the pull request, do not delete the branch. List it in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

| Option | Default | Description |
| --- | --- | --- |
| `--interactive` | off | Stop at every decision gate and wait for the user. Without it, the run approves its decision gates itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate. This includes the gates before deletion, posts to outside systems, push, and pull request creation. The run still stops for a question that blocks the work. See "Autonomy". |

To turn on `--interactive` or `--autonomous`, the user writes the flag in the request.

## Execution flow

### Phase 0: Planning

In every mode, first detect the repository root:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
```

Then, in every mode, test the branch and record the start state:

- Find the default branch with `git -C <REPO_ROOT> symbolic-ref --quiet --short refs/remotes/origin/HEAD`. It prints, for example, `origin/main`, and the default branch is the name after `origin/`. If that ref does not exist, run `git -C <REPO_ROOT> ls-remote --symref origin HEAD`, and take the branch name from its `ref: refs/heads/<name>` line. If that also gives no name, treat a branch named `main` or `master` as the default branch.
- If `git -C <REPO_ROOT> branch --show-current` prints nothing, the HEAD is detached, and a push of the commit fails later. With `--autonomous`, create a branch as the next point says. In the default mode and with `--interactive`, stop and ask the user for a branch.
- If the current branch (`git -C <REPO_ROOT> branch --show-current`) is the default branch, do not commit on it. A commit there goes straight into the default branch, and the push of Phase 5 sends it to the remote. With `--autonomous`, create a branch with `git -C <REPO_ROOT> switch -c <branch>`. If your instructions or the repository give a rule for branch names, follow it. Else use `gop/<slug>`, where `<slug>` is a short kebab-case name of the task. In the default mode and with `--interactive`, stop and ask the user. The user gives a branch name, or an explicit yes to work on the default branch. For a branch name, create that branch with the same `switch -c` command.
- Run `git -C <REPO_ROOT> status --porcelain`, and keep its paths as `start_changes`. Each line starts with two status letters and a space, and the path follows. For a rename (`old -> new`), keep both paths. A path in quotes is a path with special characters, so remove the quotes. These changes were in the working tree before the run, so Phase 5 does not commit them. Exception: if the run edits a file of `start_changes`, Phase 5 commits the whole file, with the earlier edits of the user. Name each such file in the final report.

Without `--interactive`: do not enter Plan Mode. Dispatch code-search agents and Plan agents in read-only mode. For a code search, use the agent type `dev-essentials:code-locator`. If the session does not list it, use the built-in `Explore`. Write the plan to `<REPO_ROOT>/.claude/plans/<slug>.md`, with the same content as step 2 below. Report its path in one status line, and start Phase 1. Ask the user only the open decisions of the plan. With `--autonomous`, decide them as "Autonomy" says. With `--interactive`: run steps 1 to 5 below.

1. Call the **`EnterPlanMode`** tool to turn on the built-in Plan Mode. Plan Mode allows only read-only operations and gives you a plan file. With `--interactive`, use Plan agents only inside Plan Mode, as step 2 says. Do not dispatch a Plan agent in place of Plan Mode.
2. **In Plan Mode**, follow the built-in planning workflow:
   - Explore the codebase with code-search agents to understand the relevant code, patterns, and architecture. Use the code-search agent type of Phase 0.
   - **Find the matching skills**: read the skill list in the system prompt. Identify every skill whose trigger description matches the task. Read the SKILL.md of each matching skill (with a code-search agent or the Read tool). Note its mandatory deliverables, completion checklist, and subagent delegations. Put these requirements into the plan.
   - Design the implementation approach with Plan agents.
   - Write the plan to the plan file in `.claude/plans/` (Plan Mode gives the path). Include: context, files to modify, implementation steps, design decisions, risks and assumptions, **and the mandatory artifacts of the matching skills** (tests, subagent delegations, configuration changes).
   - Review the plan against the request of the user.
3. After the plan is final, add the overview of the post-implementation pipeline to the plan, or show it to the user:

   ```markdown
   ## Post-implementation pipeline (automated)
   After implementation, the following stages run automatically:
   1. **Building** — builds affected projects, falls back to full solution
   2. **Testing** — runs the tests of the changed projects, or all tests after a change to a shared build file (skipped if no test projects found). A failed build or test goes back to implementation, at most 2 times
   3. **Validation** — reviews changes for completeness and quality
   4. **Commit & Push**: commits the files of this run. In the default mode, it pushes after the user approves it. With `--interactive`, the plan approval covers the push. With `--autonomous`, it pushes without a question.
   ```

4. Call **`ExitPlanMode`** to leave Plan Mode. This asks the user to approve the plan.
5. Record the plan file path for the later phases. If the user asks for changes instead of an approval, enter Plan Mode again and revise the plan.

### Phase 1: Implementation (main session)

6. Read `stages/01_implement.md` from the skill directory.
7. **Run its instructions yourself, in the main session.** Do NOT dispatch Phase 1 as a subagent. Phase 1 invokes skills that can dispatch subagents of their own, and Claude Code limits the depth of nested subagents. Use this context:
   - `task_description`: the user's original request
   - `plan_file_path`: path to the plan file from Phase 0
   - `repo_root`: the detected repository root
   - `validator_proposals`: (optional) list of accepted proposals from a previous validation cycle, or "None" on the first run
   - `build_test_failures`: (optional) the build errors or the failed tests of a fix cycle (see Phase 3), or "None"
8. After the implementation, record the six fields of the "Output" section of the stage file for the later phases. The fields are `modified_files`, `change_summary`, `deviations_from_plan`, `unresolved_concerns`, `applied_proposals`, and `rejected_proposals`. `modified_files` lists only the files that Phase 1 created, changed, or deleted. If Phase 1 did not edit a path of `start_changes`, that path is not in it. Keep `run_files`, the union of `modified_files` of all Phase 1 cycles of this run. Phases 2 to 4 use `run_files`, so a fix cycle keeps the test scope and the projects of the earlier cycles.

### Phase 2: Building

9. Launch a **gop-pipeline:gop-build** subagent, injecting:
    - `modified_files`: `run_files` from Phase 1
    - `repo_root`: the detected repository root
10. Capture `build_status` (SUCCEEDED/FAILED) and `build_details` from output. Add each path of its `## Fixes applied` section to `fix_files`, a list that you keep for the whole run.
11. If `build_status` is FAILED, start a fix cycle (see the end of Phase 3) with the build errors of `build_details`. Do not go on to Phase 3.

### Phase 3: Testing (conditional)

12. Choose the test scope:
    - If a modified file is a shared build file, set `test_scope` to `all`. Many projects read a shared build file at build time. Examples are `Directory.Build.props`, `Directory.Build.targets`, `Directory.Packages.props`, `global.json`, and `NuGet.config`. Such a change can break any test, so all test projects run.
    - If no shared build file changed, but a `.cs` file or a `.csproj` file changed, set `test_scope` to `changed`.
    - If neither kind of file changed, **skip this phase**, and set `test_status = "NO_TESTS_FOUND"`.

    `gop-test` does the full test-project search. If it finds no test project, it returns `NO_TESTS_FOUND`.
13. If step 12 did not skip this phase, launch a **gop-pipeline:gop-test** subagent as a background subagent, injecting the inputs below. A test run can take longer than the Bash time limit, so `gop-test` runs it in the background and waits for its notification. Only a background subagent gets that notification. If the `Agent` tool has a `run_in_background` parameter, set it to `true`. Do not ask for a foreground run.
    - `modified_files`: `run_files` from Phase 1
    - `change_summary`: from Phase 1
    - `repo_root`: the detected repository root
    - `test_scope`: from step 12
14. Capture `test_status` (PASSED/FAILED/BUILD_FAILED/NO_TESTS_FOUND) and `test_details` from output. Add each path of its `## Fixes applied` section to `fix_files`.
15. If `test_status` is FAILED or BUILD_FAILED, start a fix cycle with the failed tests and the errors of `test_details`.

A fix cycle sends a build or test failure back to the main session. `gop-build` fixes only small build breaks, and `gop-test` fixes only test code. The main session knows the plan, so it fixes the production code. In a fix cycle:

- Return to Phase 1 with `build_test_failures`: the build errors, or the failed tests with their messages. Set `validator_proposals` to "None", because the proposals of an earlier cycle are already applied. Then run Phases 2 and 3 again.
- Run at most 2 fix cycles in one run, in every mode, so that an unattended run does not loop without end. If the build or the tests still fail after the second fix cycle, stop, and report the failures to the user.
- Fix cycles do not count toward the limit of proposal re-run cycles (see "Rules").

### Phase 4: Validation (parallel fan-out)

16. **Fan out to five validator subagents in parallel.** Send a single assistant message that contains five `Agent` tool calls, one for each validator. Do not dispatch them one after another. Every subagent receives the **same** input block in its prompt (no shared state):
    - `task_description`: the user's original request
    - `plan_file_path`: path to the plan file
    - `test_status`: from Phase 3 (or "NO_TESTS_FOUND")
    - `build_status`: from Phase 2
    - `repo_root`: the detected repository root
    - `modified_files`: `run_files` from Phase 1
    - `change_summary`: from Phase 1
    - `deviations_from_plan`: from Phase 1
    - `unresolved_concerns`: from Phase 1

    Subagents launched:
    - `gop-pipeline:gop-validate-correctness` → emits `CORR-*` findings
    - `gop-pipeline:gop-validate-reuse` → emits `REUSE-*` findings
    - `gop-pipeline:gop-validate-security` → emits `SEC-*` findings
    - `gop-pipeline:gop-validate-compliance` → emits `COMP-*` findings
    - `gop-pipeline:gop-validate-performance` → emits `PERF-*` findings

17. **Collect the five per-agent reports.** Each validator emits a **rigid markdown report** (not JSON). The aggregator parses these reports deterministically, and starts only after all five reports are back. The contract every validator must follow:
    - Report-level fields: `## Validation status` (`APPROVED` | `APPROVED_WITH_WARNINGS` | `BLOCKED`) and `## Domain` (one of Correctness, Reuse, Security, Compliance, Performance). Then `## Summary`, `## Issues` with `### Critical` / `### Warnings` / `### Info` subsections, and `## Recommendation`.
    - Per-finding fields (mandatory for every CRITICAL and WARNING entry): `**[<PREFIX>-nn]** <title>`, `- Severity: CRITICAL | WARNING | INFO`, `- Confidence: nn%`, `- File: <path>:<line>`, `- Description: <text>`, `- Proposal: <text>`.
    - Optional per-domain extras: `- CWE/OWASP: ...` (security), `- Expected impact: ...` (performance), `- Requirement source: ...` (compliance).
    - Validators do NOT emit an `also_seen_by` field. The aggregator adds that annotation in step 18b, and prints it in step 18d.

18. **Aggregate into one unified validation report:**
    a. **Parse and merge.** Extract each finding record from the five markdown reports using the fields listed above. Build one combined list. Keep the ID prefix of each finding (CORR-, REUSE-, SEC-, COMP-, PERF-), so that its domain stays traceable.
    b. **Deduplicate.** Two findings collapse into one only in this case: **both** have the same `File: <path>:<line>` coordinate (or near-adjacent lines on the same logical element), AND their descriptions overlap in meaning. Keep the finding with the **higher Confidence %**. On the kept finding, add an `also_seen_by: [<dropped-ID>, ...]` annotation. The aggregator writes it, not a validator. It shows reviewers that more than one lens agreed, which is evidence strength, not noise. If the descriptions disagree in a real way, keep both findings.
    c. **Compute overall `validation_status`**, with the first rule that matches. A finding that counts as dismissed does not count here (see the last rule of `references/interactive-routing.md`):
       - A surviving finding has `Severity: CRITICAL`: `BLOCKED`.
       - Else, a surviving finding has `Severity: WARNING`: `APPROVED_WITH_WARNINGS`.
       - Else: `APPROVED`.
    d. **Render the unified report** grouped by severity first (CRITICAL → WARNING → INFO), then by domain (Correctness, Reuse, Security, Compliance, Performance) within each severity. For each finding that kept an `also_seen_by` annotation, print the annotation inline, so that the user can see that two lenses agreed. Example: `[SEC-02] ... [also seen by: REUSE-03]`.

19. **Route based on aggregated status and confidence (Human-in-the-Loop):**

    Without `--interactive`, decide yourself. For `APPROVED_WITH_WARNINGS`, accept every proposal with a confidence of 90% or more. For `BLOCKED`, accept every CRITICAL proposal, and every other proposal with a confidence of 90% or more. List the proposals that you did not accept in the final report. If you accepted a proposal, return to Phase 1 with the accepted proposals, and re-run Phases 2-4. Else proceed to Phase 5. A proposal that needs a critical decision outside the plan is a question for the user. With `--autonomous`, decide it as "Autonomy" says. With `--interactive`, read `references/interactive-routing.md`, and route as that file says.

### Phase 5: Finalization

20. Collect the files of this run: each path of `run_files` and of `fix_files`. Do not add other paths from `git status`. A file that the user or a tool wrote during the run is not part of the run, and the commit must not take it. Launch a **gop-pipeline:gop-commit** subagent, and inject `repo_root`, `files`, `push`, `warning_note`, and `commit_trailer`. In the default mode, set `push: no`. Then ask the user to approve the push. After the approval, run the push yourself: `git -C <repo_root> push`. For a branch with no upstream, run `git -C <repo_root> push -u origin HEAD`. Never force-push. With `--interactive`, set `push: yes`, because the plan approval covers the push. With `--autonomous`, set `push: yes`, and do not ask.
    - `repo_root`: the detected repository root
    - `files`: the files of this run, relative to `repo_root`
    - `push`: `yes` or `no`
    - `warning_note`: if the user dismissed CRITICAL findings at step 19, the text `Validation override: the user dismissed these CRITICAL findings:` and one line for each dismissed finding (`[<ID>] <title>`). Else `None`.
    - `commit_trailer`: if your instructions for this session ask for a commit trailer, for example a `Co-Authored-By` line, that trailer text. Else `None`.
21. Report the final result to the user: commit hash, push status, the "Not committed" list of `gop-commit`, and any warnings from validation.

## Stages

| Order | Agent | Model | Phase | Purpose |
|-------|-------|-------|-------|---------|
| 0 | *(built-in Plan Mode with `--interactive`, else code-search and Plan agents)* | inherited for Plan Mode, `haiku` for `dev-essentials:code-locator`, and the default of each built-in agent for `Explore` and Plan agents | Planning | Create implementation plan |
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

- Always start with the planning phase. Never skip to implementation.
- Without `--interactive`, the plan is auto-approved (see "Autonomy"). With `--interactive`, never proceed to implementation without user approval of the plan.
- If the plan needs revision after partial implementation: without `--interactive`, revise the plan file, report the change, and ask only for a critical decision (with `--autonomous`, decide it as "Autonomy" says). With `--interactive`, pause and re-align with the user.
- Phases 2-5 run as typed subagents with their own model and the smallest set of tools that they need. Pass data in the prompt, not through shared state. Subagents read files (plan, code) directly from the filesystem, so pass paths, not content.
- If the build or the tests still fail after the fix cycles of Phase 3, stop the pipeline and report to the user.
- With `--interactive`, only aggregated validation status of BLOCKED or APPROVED_WITH_WARNINGS triggers user interaction mid-pipeline. Without it, step 19 decides. Other failures are hard stops.
- After a re-run of Phase 1 with validator proposals, the full pipeline (Phases 1–4) runs again, with all five validators in parallel. Do not skip build, test, or any validator after a proposal-driven re-implementation.
- Limit proposal re-run cycles to 2 iterations. After the second re-run, do not start a third one. If validation still finds CRITICAL issues, stop the pipeline and escalate to the user with the full history of aggregated findings. Else proceed to Phase 5, and list the warnings that remain in the final report. With `--interactive`, first show the remaining warnings. Offer only two options: proceed to the commit, or stop for a manual fix.
