---
name: git-worktree-management
description: Creates, lists, and removes git worktrees at `<repo-root>/.claude/worktrees/<full-branch-ref>/`, one isolated folder for each task. Use it for requests to create, list, or remove worktrees. Example requests are "new worktree for Task 123456", "list my worktrees", "remove all worktrees", and "set up worktree for branch feature/tasks/1370383-foo". Triggers on requests like "create worktree", "new worktree", "list worktrees", "remove worktree", "clean up worktrees".
---

# Git Worktree Management Skill

## Purpose

Manages git worktrees inside the repo at `.claude/worktrees/<full-branch-ref>/`. Each branch gets its own folder, so you can work on several branches at the same time. Repos usually gitignore this path (`**/.claude/worktrees/`), and Workflow A Step 4 makes sure of it. So worktrees stay out of `git status` and need no cleanup outside the repo.

To get the approval prompts of Workflow A, write `--interactive` in the request. To also remove the approval prompts of Workflows C and D, write `--autonomous` in the request.

---

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
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Workflow A: Creating a New Worktree

### Pre-check: Gather required information

**CRITICAL: NEVER invent or guess branch names, task numbers, or descriptions.**

You need:

- The full branch ref (for example `feature/tasks/1370383-foo`). It can include any prefix segment. Do not flatten it, and do not drop a segment.
- A short description. You need it only with `--interactive`, for your approval prompt. The path comes only from the branch ref.

If the user did not give the branch ref, STOP and ask. With `--interactive`, also ask for the description:

> To create a worktree I need:
>
> 1. The full branch ref (for example `feature/tasks/1370383-add-feature`)
> 2. A short description of the task (only for the approval prompt)

### Step 1: Get repository root

```bash
git rev-parse --show-toplevel
```

### Step 2: Determine base branch

```bash
git symbolic-ref refs/remotes/origin/HEAD
```

The output looks like `refs/remotes/origin/main`. Take the branch name from it. If the base branch is ambiguous, ask the user.

### Step 3: Construct path and ask for confirmation

Path rule: `<repo-root>/.claude/worktrees/<full-branch-ref>/`

Copy the branch ref as it is, with its slashes. Do not flatten it.

Example: the branch `feature/tasks/1370383-terminate-reservation` gives the path `.claude/worktrees/feature/tasks/1370383-terminate-reservation`.

**Without `--interactive` (default):** announce the settings below in one status line, then continue to Step 4.

**Pipeline mode (in every mode)**: an orchestrator skill (for example `dev-essentials:feature-pipeline`) can announce the resolved path and branch. It can also state that the user authorized creation by starting the pipeline. In that case, Step 3 is done. Skip the prompt and continue to Step 4. The orchestrator is the approval gate in this case.

**With `--interactive`, STOP and show an approval prompt before you create the worktree:**

> I will create a worktree with the following settings:
>
> - **Path:** `<repo-root>/.claude/worktrees/<full-branch-ref>/`
> - **Branch:** `<branch-ref>` (new) or existing local/remote branch
> - **Base:** `<base-branch>`
>
> Do you approve? Or do you want a different path or branch?

Wait for an explicit yes. Do not continue without it.

### Step 4: Verify `.claude/worktrees/` is gitignored

```bash
git check-ignore -v .claude/worktrees/placeholder
```

If the path is NOT gitignored: without `--interactive`, add the line `.claude/worktrees/` to the local exclude file `$(git rev-parse --git-common-dir)/info/exclude`. Git does not track that file. Tell the user in one line. With `--interactive`, tell the user:

> `.claude/worktrees/` is not gitignored in this repo. Worktrees placed here will appear in `git status`. Do you want me to add `.claude/worktrees/` to `.gitignore` before continuing?

Wait for the user's answer. Do not add it silently.

### Step 5: Create the worktree

Three cases, by the state of the branch:

**Case A, new branch (most common):**

```bash
git fetch origin <base-branch>
git worktree add -b <branch-ref> <path> origin/<base-branch>
```

**Case B, the branch already exists locally:**

```bash
git worktree add <path> <branch-ref>
```

Do not pass `-b` here. With `-b`, the command fails for an existing branch.

**Case C, the branch exists on the remote only:**

```bash
git fetch origin <branch-ref>
git worktree add --track -b <branch-ref> <path> origin/<branch-ref>
```

### Step 6: Post-create bootstrap (mandatory — run every time)

Run all three sub-steps immediately after `git worktree add`, before dispatching any subagent into the worktree:

```bash
# 1. Unset upstream tracking — prevents "git branch -vv" hiding local commits
#    behind the base branch and stops accidental push/pull to the wrong target
git -C <worktree-path> branch --unset-upstream

# 2. Copy gitignored Claude Code config from master worktree so subagents
#    inherit the same allow-list, hooks, and permissions without re-prompting
[ -f .claude/settings.local.json ] && cp .claude/settings.local.json <worktree-path>/.claude/settings.local.json
# Note: inspect .gitignore for other .claude/... patterns (e.g., local CLAUDE.md
# overrides, .claude/state/, plugin caches) and replicate each one the same way.

# 3. Create a Notes/ directory for plans, drafts, and scratch files
mkdir -p <worktree-path>/Notes
```

### Step 7: Find solution file and report

Locate the first `.sln` file under the worktree root using your shell:

**PowerShell:**

```powershell
Get-ChildItem -Path <full-worktree-path> -Filter *.sln -Recurse |
    Select-Object -First 1 -ExpandProperty FullName
```

**bash (macOS / Linux / Git Bash):**

```bash
find <full-worktree-path> -name '*.sln' -type f | head -1
```

Report to the user:

- Worktree path (absolute)
- Branch name
- Base branch
- Open commands:

```powershell
# VS Code
code <full-worktree-path>

# Rider (if .sln found)
rider <path-to-sln-file>
```

---

## Workflow B: Listing Existing Worktrees

```bash
git worktree list
```

Present the output showing path, branch, and commit hash. Note which entry is the main worktree.

---

## Workflow C: Removing a Single Worktree

**Whoever runs this workflow executes it**. If you were dispatched to remove a worktree, run Steps 1 to 3 yourself. Do not dispatch another subagent for the removal (see `dev-essentials:subagent-orchestration` Rule 7). Also read the PR status of Step 1 yourself. `dev-essentials:subagent-orchestration` Rule 4 allows one small GitHub MCP call without a subagent.

### Step 1: Check PR status before removing

**Default rule:** a worktree must stay until its PR is merged. Before the removal, find out the PR status:

- If you know the PR, read its status through GitHub MCP (see `dev-essentials:github-mcp-conventions`). Else, ask the user for the PR ID or URL.
- Find out whether the PR is merged (GitHub: `merged: true`, or `state: closed` with `merged_at` set).

**User-directed override**. If the user explicitly asks to remove this specific worktree, continue, also if the PR is still open or no PR exists. Examples of such a request: "remove this worktree", "clean up the worktree", and "you can drop the worktree now". Tell the user that the worktree goes away before the PR is merged. Then continue to Step 2.

If the PR is still open or in review **and the user did not explicitly ask for the removal**, do NOT remove the worktree. Tell the user.

### Step 2: Get confirmation

Show the worktree path and branch. Ask for explicit yes. With `--autonomous`, show them and continue without the question.

### Step 3: Remove

**Before the first removal attempt, archive anything worth keeping** (for example `Notes/` drafts and task artifacts) to a location outside the worktree. A removal can fail halfway: git unregisters the worktree but leaves part of the folder on disk. So do not wait for a failed attempt before you archive.

```bash
git worktree remove <path>
git worktree list   # verify removal
```

**Never use `rm -rf` as a first resort.** On Windows, `Permission denied` on removal is usually NOT an IDE file lock. Work through this diagnosis in order:

1. **Step 1: shell CWD (the main cause, always first)**. The Bash tool and the PowerShell tool each keep their OWN current folder (CWD) between calls. An earlier `cd <worktree>` or `Set-Location <worktree>` can leave it inside the worktree, also through a build or test run. Windows then treats the folder as in use. Git or `Remove-Item` reports this as `Permission denied`, with no IDE involved. Move the CWD of BOTH shells out first:

   ```bash
   cd <repo-root>              # Bash
   ```

   ```powershell
   Set-Location <repo-root>    # PowerShell
   ```

   Then run `git worktree remove <path>` again. If a folder remains, run a plain `Remove-Item -Recurse -Force <path>` (or `rm -rf <path>`). For a worktree path of short or medium length, this step alone is enough.

2. **Step 2: long path (use it only after Step 1 failed)**. The worktree path plus a deep source tree often exceeds the Windows `MAX_PATH` limit of 260 characters. This also shows as `Permission denied`. You can try the PowerShell extended-path literal first:

   ```powershell
   Remove-Item -LiteralPath '\\?\<absolute-worktree-path>' -Recurse -Force
   ```

   The sandbox of the session can block the `\\?\` literal. If it is blocked or rejected, go to Step 3 at once.

3. **Step 3: leaf-first manual walkup (the reliable fallback)**. Delete the deepest files and folders first, and work up to the worktree root, for example with repeated `rmdir` or `Remove-Item` calls. No single call then needs the full long path. So this step also works without Step 2.

The worktree path comes from the branch ref. So keep branch-ref slugs short at creation time (see Workflow A), and Steps 2 and 3 are necessary less often.

Tell the user which step fixed the error. Do not force a removal past a real refusal for uncommitted changes.

---

## Workflow D: Removing All Worktrees

**CRITICAL: Never remove the main worktree**.

**Remove only the worktrees whose PRs are merged**.

### Step 1: List worktrees

```bash
git worktree list
```

### Step 2: Identify secondary worktrees and discover their PRs

For each secondary worktree (path contains `.claude/worktrees/`), derive its branch ref and determine PR merge status using the following procedure:

1. **Derive the branch ref** from the worktree path: strip the repo root and the `.claude/worktrees/`
   prefix from the absolute path. The remainder is the branch ref (slashes intact).
   Example: `/repo/.claude/worktrees/feature/tasks/1370383-foo` → `feature/tasks/1370383-foo`.

2. **Determine PR status via the appropriate platform:**
   - **GitHub:** call `mcp__plugin_github_github__list_pull_requests` with `owner`, `repo`, `head: "<owner>:<branch-ref>"`, and `state: "all"`. The default state lists open PRs only, and GitHub ignores a `head` value without the `<owner>:` prefix. Get `owner` and `repo` as `dev-essentials:github-mcp-conventions` Rule 1 says, and pass them on every call (Rule 2). The list can show `merged: false` for a merged PR. So read each PR that comes back with `mcp__plugin_github_github__pull_request_read` (`method: "get"`, `pullNumber`). If the PR has `merged: true`, or if it has `state: closed` and a non-null `merged_at`, the worktree is eligible for removal.
   - **Other platforms:** use the equivalent task-provider MCP server. If no MCP tool is available for the platform, **STOP and ask the user** for the PR status for that specific worktree.

3. **Apply the merged filter**. If the PR status that you read does not say that the PR is merged, the worktree is not eligible for removal. Any other status (open, draft, closed without a merge, or no PR found) means that you must NOT remove the worktree automatically.

4. **If discovery fails or is ambiguous**, **STOP and ask the user** about that specific worktree: its PR status, or whether to remove it. Examples: MCP is not available, several PRs come back for the same source branch, or no PR comes back but the branch looks active. Do NOT guess or silently skip. With `--autonomous`, do not stop: keep that worktree, and name it in the final report.

Worktrees with open or undiscoverable PRs must NOT be removed.

### Step 3: Show list and ask for confirmation

```text
Found the following merged-PR worktrees eligible for removal:
  - .claude/worktrees/feature/tasks/1370383-foo  (branch: feature/tasks/1370383-foo)

The following worktrees have open/active PRs and will be kept:
  - .claude/worktrees/bugfix/1250312-bar

The main worktree will be preserved.

Proceed with removing the 1 eligible worktree? (yes/no)
```

Without `--autonomous`, **STOP and wait for an explicit yes.** With `--autonomous`, show the list and continue.

### Step 4: Remove each eligible worktree

For each path, first archive anything worth keeping, as Workflow C Step 3 says. Whoever runs this workflow also removes each eligible path itself. The Rule 7 note of Workflow C applies to each path here too, not only to the removal of a single worktree.

```bash
git worktree remove <path-1>
git worktree remove <path-2>
# ...
git worktree prune
```

---

## Lifecycle Rule: Keep Until PR Is Merged

**Do NOT remove a worktree at the end of a session, at the end of a pipeline, or after the question "are we done?"**.

PR review feedback, follow-up fixes, and build and test runs at the branch HEAD all need the worktree.

You can remove a worktree in two cases. First, the PR is merged, by the rule of the provider (GitHub: `merged: true`, or `state: closed` with `merged_at` set). Second, the user explicitly asks to remove a specific worktree (see Workflow C). Before each removal, read the PR status again.

---

## Recreate-If-Missing Fallback

The worktree can be missing despite the lifecycle rule, for example after a manual removal, an IDE prune, or `git worktree prune`. If the branch has an active PR, recreate the worktree before you do any work.

**Before you delete any stub directory,** find out whether its path starts with `.claude/worktrees/`. If it does not, do not use this fallback on that path. Try the git-native removal first (`git worktree remove --force`). It follows the safety model of git for an entry that git registered but that is missing on disk. If a physical directory still exists after that (an unregistered orphan stub), list its contents. Then ask the user for an explicit yes before you delete it. The path can hold `Notes/` files or other files that you cannot recover, because the whole `.claude/worktrees/` subtree is gitignored. Never silently `rm -rf` a stub directory. With `--autonomous`, do not delete such a folder. List it in the final report.

```bash
git fetch origin <branch-ref>
# Only for a path under .claude/worktrees/ (see the rule above).
git worktree remove --force .claude/worktrees/<branch-ref> 2>/dev/null || true
# If a directory remains: list it and ask the user. Never chain a blind `rm -rf`.
```

Then recreate the worktree at `.claude/worktrees/<branch-ref>` with Workflow A Step 5. If `git branch --list <branch-ref>` prints a line, use Case B. If it prints nothing, the local branch is gone, so use Case C. After that, run all of Workflow A Step 6 (the post-create bootstrap).

Then work in the recreated worktree. Do not work from the main worktree through `git show <branch>:<path>`.

---

## Error Handling

**Worktree path already exists:** Inform the user. Options: remove the existing one, or list with `git worktree list` to investigate.

**Cannot remove main worktree:** The main repo worktree cannot be removed with this skill. Only secondary worktrees under `.claude/worktrees/` can be removed.

**Uncommitted changes in worktree:** Git will refuse removal. Ask the user to commit or stash first. With `--autonomous`, keep that worktree, and name it in the final report. Do not suggest `--force` removal without an explicit warning that uncommitted changes will be lost.

**Permission denied on removal:** On Windows, this is usually NOT an IDE file lock. Work through the ordered diagnosis in Workflow C Step 3. Do not report an IDE lock and stop. Never blind force-remove.
