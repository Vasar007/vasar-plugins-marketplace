These are inline instructions for the implementation phase, executed directly in the main session.
This phase runs in the main session (not as a subagent) so that it can invoke skills that spawn their own subagents.

## Context

You have access to:
- `task_description`: the user's original request
- `plan_file_path`: path to the plan file
- `repo_root`: repository root path
- `validator_proposals`: (optional) accepted proposals from a prior validation cycle — "None" on first run

## Steps

1. Read the plan file at `plan_file_path`.
2. **Check for validator proposals**: If `validator_proposals` is not "None", this is a proposal-driven re-implementation cycle. In this case:
   - Read the proposals list. Each proposal specifies a target file, what to change, and why (with a confidence percentage and finding ID).
   - Treat proposals as **additional plan steps** that supplement the original plan. The original plan's changes are already applied from the previous implementation cycle — do NOT re-implement the original plan from scratch.
   - For each proposal: locate the target file, understand the context around the change site, and apply the fix as described in the proposal.
   - If a proposal conflicts with the original plan or another proposal, note it as a deviation.
   - After applying all proposals, skip to the Output step (skills are already loaded and assumptions already verified from the first run).
3. **Load matching skills**: before coding, review the list of available skills in the system prompt. Identify every skill whose trigger description matches the current task. **Invoke each matching skill via the Skill tool** to load its full workflow, checklists, and subagent delegation instructions. Loaded skills may define mandatory artifacts (tests, subagent calls, configuration files) that the plan omitted — treat the loaded skill's workflow as authoritative and follow it alongside the plan.
4. **Verify assumptions**: before coding, check that:
   - Files listed in the plan still exist at the expected paths
   - Patterns/conventions referenced in the plan are still present
   - No conflicting changes have been made since the plan was created
   If any assumption is invalid, note it as a deviation but continue if the intent is clear.
5. **Implement changes** following the plan's steps. When a loaded skill defines its own step-by-step workflow, follow that workflow — it takes precedence over the plan for the domain it covers, because skills encode mandatory deliverables (tests, subagent delegations) that the plan may have omitted.
6. Follow existing codebase patterns and conventions identified in the plan.
7. After all changes are made, run `git diff --stat` to verify the scope of modifications.
8. Compare the diff against **both** the plan's file list **and** every loaded skill's completion checklist. If a loaded skill lists a mandatory artifact that is missing from the diff, implement it before finishing.

## Output

After completing implementation, record the following for use in subsequent phases:
- `modified_files`: list of files changed
- `change_summary`: brief description of what was done
- `deviations_from_plan`: any differences from the plan, with reasons — or "None"
- `unresolved_concerns`: anything the next stages should be aware of — or "None"
- `applied_proposals`: list of proposal IDs (e.g., CRITICAL-01, WARN-02) that were successfully applied — or "None"
- `rejected_proposals`: list of proposal IDs that could not be applied, with reasons — or "None"

## Rules

- Follow the plan as closely as possible. The plan was approved, by the user or by the default approval of the run.
- If the plan is flawed or incomplete, implement what you can and clearly note deviations.
- Do NOT run builds or tests — that is handled by later stages.
- Do NOT commit or push — that is handled by the finalization stage.
- Do NOT modify test files unless the plan or a loaded skill requires it.
- All file paths should be relative to the repo root.
- You may invoke skills and spawn subagents as needed — this phase runs in the main session specifically to enable this.
