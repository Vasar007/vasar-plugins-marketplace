---
name: git-worktree-management
description: Creates and manages git worktrees at `<repo-root>/.claude/worktrees/<full-branch-ref>/` for working on tasks in isolation. Use when the user requests to create, list, or remove worktrees (e.g., "new worktree for Task 123456", "list my worktrees", "remove all worktrees", "set up worktree for branch feature/tasks/1370383-foo"). Triggers on requests like "create worktree", "new worktree", "list worktrees", "remove worktree", "clean up worktrees".
---

# Git Worktree Management Skill

## Purpose

Manages git worktrees inside the repo at `.claude/worktrees/<full-branch-ref>/` so multiple branches can be checked out simultaneously in isolation. This path is typically gitignored (`**/.claude/worktrees/`) — verify with `git check-ignore -v .claude/worktrees/placeholder` before relying on it — so worktrees do not pollute `git status` and never require cleanup outside the repo.

To get the confirmation prompts of Workflow A, write `--interactive` in the request. To also remove the confirmation prompts of Workflows C and D, write `--autonomous` in the request.

## When to Use

- User requests to create a worktree for a task or branch
- User requests to list existing worktrees
- User requests to remove one or more worktrees

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
- With `--autonomous`, do not destroy git work that has no other copy. Examples: `git branch -D` on a branch with unmerged commits destroys commits that no other branch or remote holds. A worktree removal destroys the uncommitted changes of the worktree. Do not do such an action. List it in the final report. One exception: a squash merge makes `git branch -d` refuse a branch whose content is already in the base branch. If the pull request of that branch is merged, delete the branch with `git branch -D`. Read the pull request state on GitHub, for example with `gh pr view <branch> --json state,mergedAt`. If no lookup is possible, accept `[gone]` on the upstream in `git branch -vv` as proof, and say so in the final report. This rule does not cover a context file that a cleanup step of this workflow classifies for deletion.
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
- The full branch ref (e.g., `feature/tasks/1370383-foo`). May include any prefix segment — do not flatten or drop segments.
- A short description. You need it only with `--interactive`, for your confirmation prompt. The path comes only from the branch ref.

If the user has not provided the branch ref, STOP and ask. With `--interactive`, also ask for the description:

> To create a worktree I need:
> 1. The full branch ref (e.g., `feature/tasks/1370383-add-feature`)
> 2. A short description of the task (used only to confirm your intent)

### Step 1: Get repository root

```bash
git rev-parse --show-toplevel
```

### Step 2: Determine base branch

```bash
git symbolic-ref refs/remotes/origin/HEAD
```

This returns something like `refs/remotes/origin/main`. Extract the branch name. Confirm with the user if ambiguous.

### Step 3: Construct path and ask for confirmation

Path rule: `<repo-root>/.claude/worktrees/<full-branch-ref>/`

Mirror the branch ref verbatim — slashes intact, no flattening.

Example: branch `feature/tasks/1370383-terminate-reservation` → path `.claude/worktrees/feature/tasks/1370383-terminate-reservation`

**Without `--interactive` (default):** announce the settings below in one status line, then continue to Step 4.

**Pipeline mode (both modes)**: an orchestrator skill (for example `dev-essentials:feature-pipeline`) can announce the resolved path and branch. It can also state that the user authorized creation by starting the pipeline. In that case, Step 3 is done. Skip the prompt and continue to Step 4. The orchestrator is the confirmation gate in this case.

**With `--interactive`, STOP and present a confirmation prompt before creating:**

> I will create a worktree with the following settings:
>
> - **Path:** `<repo-root>/.claude/worktrees/<full-branch-ref>/`
> - **Branch:** `<branch-ref>` (new) or existing local/remote branch
> - **Base:** `<base-branch>`
>
> Confirm? Or override path/branch?

Wait for explicit confirmation. Do not proceed without it.

### Step 4: Verify `.claude/worktrees/` is gitignored

```bash
git check-ignore -v .claude/worktrees/placeholder
```

If the path is NOT gitignored: without `--interactive`, add the line `.claude/worktrees/` to the local exclude file `$(git rev-parse --git-common-dir)/info/exclude`. Git does not track that file. Tell the user in one line. With `--interactive`, tell the user:

> `.claude/worktrees/` is not gitignored in this repo. Worktrees placed here will appear in `git status`. Do you want me to add `.claude/worktrees/` to `.gitignore` before continuing?

Wait for the user's answer. Do not add it silently.

### Step 5: Create the worktree

Three cases depending on branch state:

**Case A — new branch (most common):**

```bash
git fetch origin <base-branch>
git worktree add -b <branch-ref> <path> origin/<base-branch>
```

**Case B — branch already exists locally:**

```bash
git worktree add <path> <branch-ref>
```

(No `-b`. Using `-b` over an existing branch fails.)

**Case C — branch exists on remote only:**

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

**Whoever runs this workflow executes it.** If you were dispatched to remove a worktree, run Steps 1-3 yourself — do not re-delegate the removal to another subagent (see `dev-essentials:subagent-orchestration` Rule 7). Step 1's single PR-status check stays inline too — it's a one-shot, low-volume GitHub MCP call, which `dev-essentials:subagent-orchestration` Rule 4 already exempts from delegation.

### Step 1: Check PR status before removing

**Default rule:** a worktree must remain alive until its PR has been merged. Before removing, verify:

- Ask the user for the PR ID or URL, or check via GitHub MCP if already known (see `dev-essentials:github-mcp-conventions`).
- Confirm the PR is merged (GitHub: `merged: true` or `state: closed` with `merged_at` set) before proceeding.

**User-directed override:** if the user explicitly asks to remove this specific worktree (e.g., "remove this worktree", "clean up the worktree", "you can drop the worktree now"), proceed even if the PR is still open or has no PR. Inform the user that the worktree will be removed before the PR is merged, then continue to Step 2.

If the PR is still open or in review **and the user has not explicitly requested removal**: inform the user and do NOT remove.

### Step 2: Get confirmation

Show the worktree path and branch. Ask for explicit yes. With `--autonomous`, show them and continue without the question.

### Step 3: Remove

**Before attempting removal, archive anything worth keeping** (e.g. `Notes/`
drafts, task artifacts) to a location outside the worktree. A removal attempt
can partially succeed — git deregisters the worktree while the residual
directory tree is left behind in a partially-deleted state — so don't risk
losing something you meant to keep by archiving only after a failed attempt.

```bash
git worktree remove <path>
git worktree list   # verify removal
```

**Never use `rm -rf` as a first resort.** On Windows, `Permission denied` on
removal is usually NOT an IDE file lock — work through this diagnosis in
order:

1. **Step 1 — shell CWD (primary cause, always try first; fixes most cases).**
   The Bash tool and the PowerShell tool each hold their OWN separate,
   persistent CWD. If either shell's CWD is still parked inside the worktree
   being removed (left over from an earlier `cd <worktree> && ...` or
   `Set-Location <worktree>`, including ones implied by a build/test run),
   Windows treats the directory as in use and git/`Remove-Item` surface that
   as `Permission denied` — with no IDE involved at all. Check and move BOTH
   shells' CWD out before anything else:

   ```bash
   cd <repo-root>              # Bash
   ```

   ```powershell
   Set-Location <repo-root>    # PowerShell
   ```

   Then retry `git worktree remove <path>` and, if a residual directory
   remains, a plain `Remove-Item -Recurse -Force <path>` (or `rm -rf <path>`).
   For short/moderate branch-ref-derived worktree paths this alone succeeds —
   no long-path workaround needed.

2. **Step 2 — long path (conditional, only if Step 1 didn't fix it).**
   `<repo-root>/.claude/worktrees/<full-branch-ref>/` plus a deep source tree
   routinely exceeds Windows' `MAX_PATH` (260 chars), which surfaces as the
   same `Permission denied`. You MAY try the PowerShell extended-path literal
   as a first attempt here:

   ```powershell
   Remove-Item -LiteralPath '\\?\<absolute-worktree-path>' -Recurse -Force
   ```

   Treat this as CONDITIONALLY available, not guaranteed: this environment's
   own sandbox/safety layer has been observed to block the `\\?\` literal
   outright in some sessions. If it's rejected or blocked, don't fight it —
   fall through to Step 3 immediately.

3. **Step 3 — leaf-first manual walkup (reliable fallback).** Delete the
   deepest files/directories first and work back up toward the worktree root
   (e.g. repeated `rmdir` / `Remove-Item` starting from the deepest leaf
   paths). This avoids needing any single long-path operation on the full
   nested path at once, so it works even when Step 2 is unavailable.

Shorter branch-ref slugs reduce how often Step 2/3 are needed at all, since
the worktree path length is derived directly from the branch ref — keep
slugs tight at creation time (see Workflow A).

Report to the user which step actually fixed it. Do not force-remove past a
genuine uncommitted-changes refusal.

---

## Workflow D: Removing All Worktrees

**CRITICAL: The main worktree cannot be removed.**

**Only remove worktrees whose PRs are merged.**

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
   - **GitHub:** use `mcp__plugin_github_github__list_pull_requests` or `mcp__plugin_github_github__pull_request_read` with `owner`, `repo`, and the branch ref as `head`. Pass `owner` and `repo` verbatim per `dev-essentials:github-mcp-conventions` Rule 2. A PR is eligible for worktree removal when `merged: true` or (`state: closed` AND `merged_at` is non-null).
   - **Other platforms:** use the equivalent task-provider MCP server. If no MCP tool is available for the platform, **STOP and ask the user** for the PR status for that specific worktree.

3. **Apply the merged filter.** A worktree is eligible for removal only when its PR is confirmed merged. Any other status (open, draft, closed-without-merge, or no PR found) means the worktree must NOT be removed automatically.

4. **If discovery fails or is ambiguous** (MCP unavailable, multiple PRs returned for the same source branch, zero PRs found but the branch looks active) — **STOP and ask the user** for the PR status or removal confirmation for that specific worktree. Do NOT guess or silently skip. With `--autonomous`, do not stop: keep that worktree, and name it in the final report.

Worktrees with open or undiscoverable PRs must NOT be removed.

### Step 3: Show list and ask for confirmation

```
Found the following merged-PR worktrees eligible for removal:
  - .claude/worktrees/feature/tasks/1370383-foo  (branch: feature/tasks/1370383-foo)

The following worktrees have open/active PRs and will be kept:
  - .claude/worktrees/bugfix/1250312-bar

The main worktree will be preserved.

Proceed with removing the 1 eligible worktree? (yes/no)
```

Without `--autonomous`, **STOP and wait for explicit confirmation.** With `--autonomous`, show the list and continue.

### Step 4: Remove each eligible worktree

Archive anything worth keeping from each worktree first — Workflow C Step 3 applies per path. Likewise, whoever runs this workflow removes each eligible path itself — Workflow C's Rule 7 note applies per path here too, not just for a single-worktree removal.

```bash
git worktree remove <path-1>
git worktree remove <path-2>
# ...
git worktree prune
```

---

## Lifecycle Rule: Keep Until PR Is Merged

**Do NOT remove a worktree at end of session, end of pipeline, or when asked "are we done?".**

The worktree is needed for PR review feedback, follow-up fixes, build/test reproduction, and code inspection at the branch HEAD. Removing it early forces awkward `git show <branch>:<path>` workflows that lose build/test capability.

Removal is allowed after the PR is confirmed merged (provider-specific — for GitHub: `merged: true` or `state: closed` with `merged_at` set), or when the user explicitly asks to remove a specific worktree (see Workflow C). Always re-fetch PR status before removing to confirm.

---

## Recreate-If-Missing Fallback

If the worktree is missing despite the lifecycle rule (manual removal, IDE prune, `git worktree prune`), and the branch has an active PR, recreate before doing any work.

**Before deleting any stub directory:** verify the path starts with `.claude/worktrees/` so the fallback cannot apply to an arbitrary path. Try the git-native removal first (`git worktree remove --force`), which respects git's safety model for registered-but-missing entries. If a physical directory still exists afterwards (an unregistered orphan stub), list its contents and ask the user for explicit confirmation before deleting — the path may contain `Notes/` files or other unrecoverable artifacts (the entire `.claude/worktrees/` subtree is gitignored). Never silently `rm -rf` a stub directory. With `--autonomous`, do not delete such a folder. List it in the final report.

```bash
git fetch origin <branch-ref>
# Confirm the path is under .claude/worktrees/ before any removal step.
# 1. Try git-native removal first (covers the common case where git still
#    has the entry registered but the directory was wiped manually).
git worktree remove --force .claude/worktrees/<branch-ref> 2>/dev/null || true
# 2. If a physical orphan directory still exists, list its contents and ask
#    the user to confirm deletion. Only then remove it. Do NOT chain a blind
#    `rm -rf` here — the rule from Workflow C (Step 3) still applies.

# 3. Recreate — mirror Workflow A Step 5 branch-state logic:
#    Case B: branch still exists locally
git worktree add .claude/worktrees/<branch-ref> <branch-ref>
#    Case C: branch no longer exists locally (pruned/damaged state) — use this instead:
# git worktree add --track -b <branch-ref> .claude/worktrees/<branch-ref> origin/<branch-ref>
# Re-run the bootstrap
git -C .claude/worktrees/<branch-ref> branch --unset-upstream
[ -f .claude/settings.local.json ] && cp .claude/settings.local.json .claude/worktrees/<branch-ref>/.claude/settings.local.json
mkdir -p .claude/worktrees/<branch-ref>/Notes
```

**Branch-state decision (choose Case B or C above):**

Check whether the branch exists locally with `git branch --list <branch-ref>`.

- Output non-empty → **Case B**: use `git worktree add <path> <branch-ref>`.
- Output empty → **Case C**: the local branch is gone; use `git fetch origin <branch-ref>` (already done above) then `git worktree add --track -b <branch-ref> <path> origin/<branch-ref>`.

Then work in the recreated worktree. Do not operate from master via `git show <branch>:<path>`.

---

## Error Handling

**Worktree path already exists:** Inform the user. Options: remove the existing one, or list with `git worktree list` to investigate.

**Branch already exists locally:** Use `git worktree add <path> <branch-name>` (no `-b`). See Case B above.

**Not in a git repository:** Inform the user they need to run from inside a git repo.

**Cannot remove main worktree:** The main repo worktree cannot be removed with this skill. Only secondary worktrees under `.claude/worktrees/` can be removed.

**Uncommitted changes in worktree:** Git will refuse removal. Ask the user to commit or stash first. With `--autonomous`, keep that worktree, and name it in the final report. Do not suggest `--force` removal without an explicit warning that uncommitted changes will be lost.

**Permission denied on removal:** On Windows this is usually NOT an IDE file lock — see the ordered diagnosis in Workflow C Step 3 (shell CWD parked in the worktree is the dominant, self-inflicted cause; Windows long paths are the secondary cause on deep branch refs; leaf-first walkup is the reliable fallback). Work through that diagnosis rather than reporting an IDE lock and stopping. Never blind force-remove.

---

## Reference: Git Worktree Commands

```bash
# List all worktrees
git worktree list

# Add a new worktree (new branch) — fetch first, then branch from remote-tracking ref
git fetch origin <base-branch>
git worktree add -b <branch-ref> <path> origin/<base-branch>

# Add a worktree for an existing local branch (no -b)
git worktree add <path> <branch-ref>

# Add a worktree for a remote-only branch
git fetch origin <branch-ref>
git worktree add --track -b <branch-ref> <path> origin/<branch-ref>

# Unset upstream after creation (always)
git -C <path> branch --unset-upstream

# Remove a worktree
git worktree remove <path>

# Clean up stale references
git worktree prune

# Get repository root
git rev-parse --show-toplevel

# Get default remote branch
git symbolic-ref refs/remotes/origin/HEAD

# Check if a path is gitignored
git check-ignore -v <path>
```
