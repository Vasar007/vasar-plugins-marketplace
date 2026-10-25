These are the instructions for the implementation phase. Run them yourself in the main session, not as a subagent. Then you can invoke skills that dispatch subagents of their own.

## Context

You have access to:

- `task_description`: the user's original request
- `plan_file_path`: path to the plan file
- `repo_root`: repository root path
- `validator_proposals`: (optional) accepted proposals from a prior validation cycle, or "None" on the first run
- `build_test_failures`: (optional) the build errors or the failed tests from a fix cycle, or "None" on the first run

## Steps

1. Read the plan file at `plan_file_path`.
2. **Validator proposals**: If `validator_proposals` is not "None", this is a proposal-driven re-implementation cycle. In this case:
   - Read the proposals list. Each proposal names a target file, what to change, and why (with a confidence percentage and a finding ID).
   - Treat the proposals as **additional plan steps** on top of the original plan. The changes of the original plan are already in place from the previous cycle. Do NOT re-implement the original plan from scratch.
   - For each proposal: locate the target file, read the code around the change site, and apply the fix that the proposal describes.
   - If a proposal conflicts with the original plan or another proposal, note it as a deviation.
   - After you apply all proposals, skip to the Output section. The first run already loaded the skills and tested the assumptions.
3. **Build or test failures**: If `build_test_failures` is not "None", this is a fix cycle. The build or the tests failed after the last implementation. In this case:
   - The changes of the earlier cycles are already in place. Keep them, and fix only the failures.
   - For each failure, read the error, the failing code or test, and the code under test. Find the cause, and fix the production code.
   - Do not weaken a test to make it pass. A planned API change can make a test stale, so that it does not compile. Then update the test to the new API, and note the change as a deviation. Change a test for another reason only as the Rules allow.
   - After you fix all failures, skip to the Output section.
4. **Load matching skills**: before coding, review the list of available skills in the system prompt. Identify every skill whose trigger description matches the current task. **Invoke each matching skill via the Skill tool** to load its full workflow, checklists, and subagent delegation instructions. A loaded skill can define mandatory artifacts that the plan omitted (tests, subagent calls, configuration files). Treat the workflow of the loaded skill as authoritative, and follow it alongside the plan.
5. **Test the assumptions**: before coding, find out whether:
   - the files listed in the plan still exist at the expected paths
   - the patterns and conventions that the plan references are still present
   - no change since the plan was created conflicts with the plan
   If an assumption is false, note it as a deviation. If the intent is still clear, continue.
6. **Implement changes** following the steps of the plan. If a loaded skill defines its own step-by-step workflow, follow that workflow. For the domain that it covers, the workflow of the skill takes precedence over the plan. Skills encode mandatory deliverables (tests, subagent delegations) that the plan can omit.
7. Follow existing codebase patterns and conventions identified in the plan.
8. After all changes are made, run `git status --short` and `git diff --stat` to see the scope of the modifications, new files included.
9. Compare the diff against **both** the file list of the plan **and** the completion checklist of every loaded skill. If a loaded skill lists a mandatory artifact that is missing from the diff, implement it before finishing.

## Output

After completing implementation, record the following for use in subsequent phases:

- `modified_files`: list of files changed
- `change_summary`: brief description of what was done
- `deviations_from_plan`: any differences from the plan, with reasons, or "None"
- `unresolved_concerns`: anything that the next stages need to know, or "None"
- `applied_proposals`: list of proposal IDs that you applied (for example `CORR-01` or `SEC-02`), or "None"
- `rejected_proposals`: list of proposal IDs that you did not apply, with reasons, or "None"

## Rules

- Follow the plan as closely as possible. The plan was approved, by the user or by the default approval of the run.
- If the plan is flawed or incomplete, implement what you can, and clearly note the deviations.
- Do NOT run builds or tests. Later stages do that.
- Do NOT commit or push. The finalization stage does that.
- Do NOT modify test files. Exception: the plan or a loaded skill requires the change.
- Give all file paths relative to the repo root.
- You can invoke skills and dispatch subagents as needed. This phase runs in the main session for this reason.
