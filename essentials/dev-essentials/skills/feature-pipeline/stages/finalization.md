# Stage 9: Finalization + PR

The master agent does these steps itself, in the main session, at Step 9 of `SKILL.md`. No subagent runs them. The project root is the absolute path `{WORKTREE_PATH}`, and the main session can run in another folder. So run every git command as `git -C "{WORKTREE_PATH}" ...`. Run every other shell command (build, test, lint, push, and PR) as `cd "{WORKTREE_PATH}" && <command>`. Human Approve #2 approved the commit, the push, and the PR, or the full mode did.

## Contents

- Inputs
- Process
- Rules

## Inputs

- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/requirements.md`: for the summary and the rationale
- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/spec.md`: for the summary and the rationale
- `{WORKTREE_PATH}/{ARTIFACTS_DIR}/{TASK_ID}/review.md`: the approved review. If `--skip` removed the `review` stage, this file does not exist. Then continue without it.
- The project guidance files, the base branch, and all workflow commands of the project context
- The start changes: the paths of `startChanges` in `pipeline-state.json`, and the paths that "After the stage" in `references/stage-launch.md` noted as edits of earlier stages. If a resume or a compaction lost these notes, the edited paths are "unknown".
- The `<commit-conventions>` block of `references/commit-conventions.md`, with the cadence line of `{COMMIT_MODE}`

## Process

### Step 1: Record the Start

Do launch step 1 of `references/stage-launch.md`: make sure that each file of the "Reads" column exists. Then write the output of `git -C "{WORKTREE_PATH}" rev-parse HEAD` into `stageStartSha` (`{"finalization": "<sha>"}`), as launch step 3 says. Skip launch steps 2, 4, 5, and 6, because they pick a model and compose a prompt.

### Step 2: Discover Finalization Workflow

Before you change the git state, compare the workflow commands of the project context with the current state of the repository:

- The current branch name
- The recent commit history
- The project guidance files
- The git remotes and the metadata of the default branch
- Hints from CI and the hosting service
- Whether tools such as `gh` are available

Treat the commands of the project context (build, full test, lint, base branch, push, and PR) as the canonical workflow hints of this run.

If a critical step is still ambiguous after this comparison, stop, and report the ambiguity. Do not guess.

### Step 3: Make Sure That the State Is Clean

1. Run the build command and then the test command of the project context, one time each. This is the build and test run before the push that item 1 of "Trust but verify" in `dev-essentials:subagent-orchestration` asks for. That item gives the output filter, the exit code, and the rule for a run that can take longer than 10 minutes.
   - If the build or a test fails, stop, and report the failure. Do not fix the cause in this stage.
   - If no test command is available, say so in the final report.

2. If the project context lists a lint command:
   - Run it.
   - If it fails and a lint fix command is available, run the fix command. Then run the tests and the lint again.
   - If the lint still fails, stop.

3. Look at the git status:

   ```bash
   git -C "{WORKTREE_PATH}" status
   ```

   - **`finalization` mode (default)**: the earlier stages staged their changes. A tracked file can have an unstaged change. If its path is missing from the start changes, the change is from this run, so stage it. If the start changes name the path as an edit of an earlier stage, the change is from this run too, so stage it. Leave every other path out. Leave out each untracked file, because a stage that made a new file already staged it. List each path that you left out under "Not committed". Do not list the paths under `{ARTIFACTS_DIR}/`.
   - **`per-step` mode**: `git status` must be clean, except for untracked artifacts (for example under `{ARTIFACTS_DIR}/`) and the paths of the start changes that no stage edited. The earlier stages already committed every source change. If the tree is not clean, stop, and report the uncommitted files. Do not commit them here.

### Step 4: Create Commit (finalization-commit mode only)

**In `per-step` mode, skip this step entirely, and go to Step 5.** The earlier stages already made every commit.

On a resume, this stage can run again after its commit, because you mark it as done only after the push. If the index is clean and `HEAD` is a commit of this run that holds the changes of the run, the commit already exists. Do not commit again. Go to Step 5.

The `<commit-conventions>` block gives the format of the commit message. Follow it exactly. Do not invent your own format. Commit only the staged paths of this run, with the paths after `--`. List them with `git -C "{WORKTREE_PATH}" diff --cached --name-only --no-renames`, so that a rename lists the old path and the new path. A staged path of the start changes is a path of this run only in one case: the start changes name it as an edit of an earlier stage. If the edited paths are "unknown", leave such a path out, and list it under "Not committed".

The body gives the reason for the change. Take it from Section 1 (Task Summary) of `requirements.md`. Write it in terms of production engineering only. The rule of the block against pipeline-internal references governs the wording.

### Step 5: Push

If the project context gives no push command, say so in the final report, and do not invent a push step. If the current branch is the default branch of the repository, do not push. Stop and report it. Else run `cd "{WORKTREE_PATH}" && <push command>`. If the push fails because the history diverged, stop and report it.

### Step 6: Create the Pull Request

If the project context gives no PR command, skip this step. Report the branch status and the work that is left for the human. Else:

1. Take the base branch of the PR from the project context. If it is unsafe or a guess, stop, and report the ambiguity.
2. Write the PR title and the PR body. Take them from Section 1 (Task Summary) of `requirements.md` and Section 1 (Resolved Questions) of `spec.md`. Include the task URL from the task context, where it has one. Do not name pipeline artifacts in the title or the body, for the same reason as in the commit message.
3. Follow the convention of the repository for PR titles and bodies. Such a convention is a PR template of the repository, for example `.github/pull_request_template.md`. It can also be a PR rule in the Key Conventions or the guidance files that gives the sections of the body. A rule that asks only for some content, for example a link to the tracking issue, gives no form. Such a rule adds content to the form that the body takes. If the repository has a PR template, or gives no form for the PR body, load the skill `dev-essentials:compose-pr` with the `Skill` tool. Else do not load it. A PR rule that gives the sections of the body needs no load. For a template, follow the rules for a template in its step "5. Generate PR Description". With no form, write the body by that step: the form and the writing rules. In both cases, use the task URL as the closing line of that step. Keep the limit of its section "Length Constraints". For the count of files and lines, run `git -C "{WORKTREE_PATH}" diff --stat origin/<base branch>...HEAD`. Skip its other steps and its stop cases, because this step gives the sources and opens the PR. Do not save the draft file of its step 6.
4. If the PR command is a shell command, pass the base branch, the title, and the body with the options of the command. For `gh pr create`, first write the body to a file outside the repository, and then use `--base`, `--title`, and `--body-file`. Run `cd "{WORKTREE_PATH}" && <PR command> <options>`. If the PR command is an MCP tool name, for example `mcp__plugin_github_github__create_pull_request`, load the tool with `ToolSearch`. Then call it with the base branch, the title, the body, and these values:
   - `owner` and `repo`: the `<owner>/<repo>` that the PR creation entry of the project context names. If the entry names none, look at the Task Provider. If its MCP server prefix is the prefix of the PR tool, take its project identifier. Name the source of these values in the final report. The user wrote the project context, so these values count as supplied by the user under Rule 1 of `dev-essentials:github-mcp-conventions`.
   - `head`: the current branch, from `git -C "{WORKTREE_PATH}" branch --show-current`. If the PR creation entry names a fork owner, the PR comes from the fork of that owner. Then pass `<fork owner>:<branch>`, for example `my-user:feature/42-fix`. `owner` and `repo` still name the repository that gets the PR. Take the fork owner only from that entry, and not from a remote URL. Without a fork owner, pass the bare branch.

   If neither source names the repository, do not call the tool. Do not take the repository from the `origin` remote, from the task URL, or from the session. Stop, and report that the project context names no repository for the PR. Also report the pushed branch, so that the human can open the PR.

5. If this step created a PR on GitHub, set its fields: do the steps of `skills/github-mcp-conventions/references/pull-request-fields.md` of this plugin. From the base folder of this skill, its path is `../github-mcp-conventions/references/pull-request-fields.md`. Take `owner`, `repo`, and the number of the PR from the URL of the new PR, as that file says. Name that source in the final report. If the task URL points to a GitHub issue, it is the issue of these steps. Name each field that the run did not set in the final report.

### Step 7: Link the Tracking Issue

If Step 6 created no PR, skip this step. The task URL can point to a tracking item of the PR provider, for example a GitHub issue for a PR on GitHub. If the provider has a linking tool, load it with `ToolSearch`, and link the PR to the item. If the link fails, report the failure, and continue, because the PR exists. Without a linking tool, the task URL in the PR body is the link.

## Rules

- Never amend a commit. Never pass `--no-verify` to a commit or a push. See the `<commit-conventions>` block.
- Never force-push. Never push the default branch.
- Never include pipeline artifacts from `{ARTIFACTS_DIR}/` in the commit. They are local to the project.
- Never name `{ARTIFACTS_DIR}/...` paths, artifact section numbers, or review-finding IDs in the commit message. See the `<commit-conventions>` block.
- If a step fails (the build, the tests, the lint, the workflow inference, the push, or the PR), stop and report the failure. Do not try workarounds. A failed link of Step 7 and a field that item 5 of Step 6 did not set are the exceptions.
