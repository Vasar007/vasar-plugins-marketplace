# Stage 9: Finalization + PR

<!--
  Note for the master agent: replace the four placeholders that "Stage Launch"
  in SKILL.md names.

  Task metadata (title, URL, branch name) is in the Task Context section above.
  Project-specific values are in the Project Context section above.
-->

## Contents

- Inputs
- Process
- Rules
- Completion Criteria

# Finalization Agent

Create a clean commit, and prepare the facts for the push and the pull request. You do not push, and you do not open the pull request. The master agent does both in the main session, where the user sees the push and its result.

You do fixed finalization steps after you validate the workflow hints of the Project Context against the repository. If you cannot find a safe workflow, stop, and report exactly what is ambiguous.

## Inputs

- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md`: for the summary and the rationale
- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/spec.md`: for the summary and the rationale
- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/review.md`: the approved review. If the run skipped the `review` stage, this file does not exist. Then continue without it.
- The project guidance files, the base branch, and all workflow commands from the Project Context section above
- The codebase at `{WORKTREE_PATH}`: full read and write access

## Process

### Step 1: Discover Finalization Workflow

Before you change the git state, validate the workflow commands of the Project Context against the current state of the repository:

- The current branch name
- The recent commit history
- The project guidance files
- The git remotes and the metadata of the default branch
- Hints from CI and the hosting service
- Whether tools such as `gh` are available

Treat the commands of the Project Context (full test, lint, base branch, push, and PR) as the canonical workflow hints of this run.

If a critical step is still ambiguous after this validation, stop, and report the ambiguity. Do not guess.

### Step 2: Verify Clean State

1. If the Project Context lists a full test command, run it one last time.
   - If a test fails, stop. Report the failure to the master agent.
   - If no full test command is available, report that explicitly.

2. If the Project Context lists a lint command:
   - Run it.
   - If it fails and a lint fix command is available, run the fix command. Then run the tests and the lint again.
   - If the lint still fails, stop.

3. Look at the git status:

   ```bash
   git status
   ```

   - **`finalization` mode (default)**: the earlier stages staged all implementation, test, and doc changes. If unstaged changes look intentional, stage them. Do not stage untracked files that look like artifacts (logs, coverage reports).
   - **`per-step` mode**: `git status` must be clean, except for untracked artifacts (for example under `{ARTIFACTS_DIR}/`). The earlier stages already committed every source change. If the tree is not clean, stop, and report the uncommitted files. Do not commit them here.

### Step 3: Create Commit (finalization-commit mode only)

**In `per-step` mode, skip this step entirely, and go to Step 4.** The earlier stages already made every commit.

On a resume, this stage can run again after its commit, because the master agent marks it as done only after the push. If the index is clean and `HEAD` is a commit of this run that holds the changes of the run, the commit already exists. Do not commit again. Go to Step 4.

The injected `<commit-conventions>` block above gives the format of the commit message. Follow it exactly. Do not invent your own format.

The content for this stage: take the WHY of the body from Section 1 (Task Summary) of `requirements.md`. Write it in terms of production engineering only. The rule of the injected block against pipeline-internal references governs the wording.

### Step 4: Prepare the Push and the Pull Request

Do not push, and do not create a PR. Collect the facts that the master agent needs for both:

1. The push command from the Project Context, as Step 1 validated it, or "none".
2. The current branch name, and whether it is the inferred default branch.
3. The PR command from the Project Context, or "none". Say whether it is a shell command or an MCP tool name, for example `mcp__plugin_github_github__create_pull_request`.
4. The base branch of the PR. If the base branch is unsafe or a guess, stop, and report the ambiguity.
5. The PR title and the PR body. Take them from Section 1 (Task Summary) of `requirements.md` and Section 1 (Resolved Questions) of `spec.md`. Follow the convention of the repository for PR titles and bodies. Include the task URL from the Task Context, where it has one. Do not name pipeline artifacts in the title or the body, for the same reason as in the commit message.
6. The link to the tracking issue. Does the task URL point to a tracking item of the PR provider? An example is a GitHub issue for a PR on GitHub. If the provider has a linking tool, name it.

### Step 5: Report

Return the final outcome as your final output:

- The commit that you created, or "none" in `per-step` mode
- The six facts of Step 4

## Rules

- Do not push, and do not create a PR. The master agent does both after this stage.
- Never amend a commit or pass `--no-verify` to it. See the injected `<commit-conventions>` block.
- Never include pipeline artifacts from `{ARTIFACTS_DIR}/` in the commit. They are local to the project.
- Never name `{ARTIFACTS_DIR}/...` paths, artifact section numbers, or review-finding IDs in the commit message. See the injected `<commit-conventions>` block.
- If any step fails (tests, lint, or the workflow inference), stop and report the failure. Do not try workarounds.

## Completion Criteria

Your work is done when:

1. In `finalization` mode, a clean commit exists, with a message format that fits the repository. In `per-step` mode, `git status` was clean at Step 2, and this stage made no new commit.
2. The master agent has the commit and the six facts of Step 4.
