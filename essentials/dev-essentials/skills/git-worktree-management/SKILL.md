---
name: git-worktree-management
description: Creates, lists, and removes git worktrees in the `.claude/worktrees/` folder of the repo, one folder for each task, named by its full branch ref.
when_to_use: Use it for "create worktree", "list worktrees", "remove worktree", or "clean up worktrees".
---

# Git Worktree Management Skill

## Purpose

Manages git worktrees inside the repo at `.claude/worktrees/<full-branch-ref>/`. Each branch gets its own folder, so you can work on several branches at the same time. Repos usually gitignore this path (`**/.claude/worktrees/`), and Workflow A Step 4 makes sure of it. So worktrees stay out of `git status` and need no cleanup outside the repo.

The script `scripts/worktree.py` of this skill does the fixed git steps: the path rule, the ignore check, `git worktree add` in its three cases, the bootstrap, `git worktree remove`, and `git worktree prune`. You keep each step that needs a judgment, a question to the user, or a GitHub MCP tool. The script needs Python 3 and git 2.31 or later. On Windows, run it in the Bash tool (Git Bash). It asks for no input, and it refuses each path outside `.claude/worktrees/`.

To get the approval prompts of Workflow A, write `--interactive` in the request. To also remove the approval prompts of Workflows C and D, write `--autonomous` in the request.

---

## Autonomy

This workflow has three modes. The user picks one with a flag: the default (no flag), `--interactive`, or `--autonomous`. A gate is a step where the run can stop and ask the user. This table lists each gate of this workflow and what each mode does there.

| Gate | Default | `--interactive` | `--autonomous` |
| --- | --- | --- | --- |
| Workflow A Step 3: create | Announce the path and the branch, and continue | Approval prompt | Same as default |
| Workflow A Step 4: path not gitignored | Add it to `info/exclude`, and say so | Ask | Same as default |
| Workflow C Step 2: remove one worktree | Ask for a yes | Same | Show the path, and continue |
| Workflow D Step 3: remove the merged worktrees | Ask for a yes | Same | Show the list, and continue |
| Workflow D Step 2 item 4: unknown PR status | Ask | Same | Keep the worktree, and report it |
| Uncommitted changes | Ask the user to commit or stash | Same | Keep the worktree, and report it |
| Recreate-If-Missing: an orphan stub folder | List its contents, and ask for a yes before the deletion | Same | Do not delete it, and list it in the final report |

Pipeline mode skips the Workflow A Step 3 prompt in every mode.

These rules apply in every mode:

- If the work cannot continue without an answer, ask the user. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that the run cannot fix also stops the run. Do not ask in other cases.
- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default of the gate, and continue.
- The final report lists each gate that the run passed without a stop. With `--autonomous`, it also lists each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It adds no steps. A step that runs only with a flag such as `--push` still needs that flag, and the flag is the approval of that step.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- With `--autonomous`, do not destroy git work that has no other copy. Examples: a branch with unmerged commits, or a worktree with uncommitted changes. List such an action in the final report instead.

## Workflow A: Creating a New Worktree

### Pre-check: Gather required information

**Never invent or guess branch names, task numbers, or descriptions.**

You need:

- The full branch ref (for example `feature/tasks/1370383-foo`). It can include any prefix segment. Do not flatten it, and do not drop a segment.
- A short description. You need it only with `--interactive`, for your approval prompt. The path comes only from the branch ref.

If the user did not give the branch ref, stop and ask. With `--interactive`, also ask for the description:

> To create a worktree I need:
>
> 1. The full branch ref (for example `feature/tasks/1370383-add-feature`)
> 2. A short description of the task (only for the approval prompt)

### Step 1: Get repository root

The script takes the main worktree as the repository root: the first entry of `git worktree list`. Also from a linked worktree, the root is the main worktree. The `REPO` line of the script names the root.

### Step 2: Determine base branch

For a new branch, the base is the branch of `origin/HEAD`. If the caller names a base branch, pass it with `--base <base-branch>`. The script uses the base only for a new branch, and its `BASE` line names the base and where it came from. If the script refuses because `origin/HEAD` is not set, ask the user for the base branch.

### Step 3: Construct path and ask for confirmation

Path rule: `<repo-root>/.claude/worktrees/<full-branch-ref>/`

Copy the branch ref as it is, with its slashes. Do not flatten it. The script builds the path by this rule.

Example: the branch `feature/tasks/1370383-terminate-reservation` gives the path `.claude/worktrees/feature/tasks/1370383-terminate-reservation`.

**Without `--interactive` (default):** announce the settings below in one status line, then continue to Step 4.

**Pipeline mode (in every mode)**: an orchestrator skill (for example `dev-essentials:feature-pipeline`) can announce the resolved path and branch. It can also state that the user authorized creation by starting the pipeline. In that case, Step 3 is done. Skip the prompt and continue to Step 4. The orchestrator is the approval gate in this case.

**With `--interactive`, stop and show an approval prompt before you create the worktree.** First run the plan form. It prints the `PATH`, `CASE`, and `BASE` lines, and it changes nothing. If no caller named a base branch, leave out `--base`:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" create <branch-ref> --base <base-branch> --plan
```

Show these lines in the prompt:

> I will create a worktree with the following settings:
>
> - **Path:** `<repo-root>/.claude/worktrees/<full-branch-ref>/`
> - **Branch:** `<branch-ref>` (new) or existing local/remote branch
> - **Base:** `<base-branch>`
>
> Do you approve? Or do you want a different path or branch?

Wait for an explicit yes. Do not continue without it.

### Step 4: Verify `.claude/worktrees/` is gitignored

The script checks the ignore rule with `git check-ignore`. Its `IGNORE` line names the rule that ignores the folder, or says that no rule does.

If the path is not gitignored: without `--interactive`, pass `--add-exclude` in Step 5. The script then adds the line `.claude/worktrees/` to the local exclude file `info/exclude` of the common git folder, and prints an `EXCLUDE` line. Git does not track that file. Tell the user in one line. With `--interactive`, tell the user:

> `.claude/worktrees/` is not gitignored in this repo. Worktrees placed here will appear in `git status`. Do you want me to add `.claude/worktrees/` to `.gitignore` before continuing?

Wait for the user's answer. Do not add it silently. On a yes, add the line `.claude/worktrees/` to `.gitignore`. If the user wants the local exclude file instead, pass `--add-exclude` in Step 5.

### Step 5: Create the worktree

Run the script with the branch ref. Pass `--base` as Step 2 says, `--add-exclude` as Step 4 says, and `--notes-dir` as Step 6 says:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" create <branch-ref> --base <base-branch> --add-exclude --notes-dir <notes-folder>
```

The script picks one of three cases by the state of the branch. Its `CASE` line names the case:

- Case A, a new branch (most common): it fetches the base branch from `origin`, and runs `git worktree add --no-track -b <branch-ref> <path> origin/<base-branch>`.
- Case B, the branch already exists locally: it runs `git worktree add <path> <branch-ref>`, with no `-b`.
- Case C, the branch exists on the remote only: it fetches the branch, and runs `git worktree add --no-track -b <branch-ref> <path> origin/<branch-ref>`.

Read the exit code and the last line, `RESULT`:

- Exit code 0, `RESULT: CREATED`: the script also ran Step 6. Go to Step 7.
- Exit code 3, `RESULT: REFUSED`: nothing changed. Each `REFUSED` line gives a reason. Tell the user the reason. For a path that exists, see "Error Handling".
- Exit code 1, `RESULT: FAILED`: no worktree exists. Report each `FAILED` line and each `LEFT` line to the user, and stop. Do not make the worktree in another way, for example with a plain `git worktree add` or a copy of the repository.
- Exit code 1, `RESULT: CREATED, BUT`: the worktree exists, but a sub-step of Step 6 failed. Do the sub-step of each `FAILED` line by hand, as Step 6 describes it.
- Exit code 2: the script cannot run, for example with no `python3` or with git older than 2.31. Report its error, and stop.

### Step 6: Post-create bootstrap (mandatory — run every time)

The create command of Step 5 runs these three sub-steps right after `git worktree add`. So they are done before you dispatch a subagent into the worktree. Each sub-step prints one line:

1. `UPSTREAM`: if the branch has an upstream, the script removes it with `git branch --unset-upstream <branch-ref>`. Then `git branch -vv` does not hide local commits behind the base branch, and no push or pull goes to the wrong target. Push with an explicit `origin <branch-ref>`.
2. `SETTINGS`: the script copies `.claude/settings.local.json` of the main worktree into the worktree, so that subagents get the same allow-list, hooks, and permissions with no new prompt. If git does not ignore the file, or if the branch has its own copy, the script does not copy it. Look in `.gitignore` for other ignored files below `.claude/`, for example a local CLAUDE.md override or `.claude/state/`. Copy each one yourself in the same way.
3. `NOTES`: the script makes the notes folder for plans, drafts, and scratch files. Pass the folder with `--notes-dir`. The configured notes folder is ${user_config.notes_dir}. If that value still shows as a placeholder, no value is saved: use Notes. A location that the CLAUDE.md of the repo names wins.

### Step 7: Find the solution or project file and report

Locate the first solution or project file under the worktree root with your shell. The commands below show the .NET case: the first `.sln` or `.slnx` file. For another stack, search for its own solution or project file instead.

**PowerShell:**

```powershell
Get-ChildItem -Path <full-worktree-path> -Include *.sln,*.slnx -Recurse -File |
    Select-Object -First 1 -ExpandProperty FullName
```

**bash (macOS / Linux / Git Bash):**

```bash
find <full-worktree-path> -type f \( -name '*.sln' -o -name '*.slnx' \) | head -1
```

Report to the user:

- Worktree path (absolute)
- Branch name
- Base branch
- Open commands for the editor (for example, VS Code or Rider):

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

If the PR is still open or in review **and the user did not explicitly ask for the removal**, do not remove the worktree. Tell the user.

### Step 2: Get confirmation

Run the plan form of the removal. The branch ref is the path below `.claude/worktrees/`, as Workflow D Step 2 item 1 says. The plan form changes nothing:

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" remove <branch-ref>
```

Show the `PATH` line, the `BRANCH` line, and each `IGNORED` line. The removal deletes the ignored files that the `IGNORED` lines name. Ask for explicit yes. With `--autonomous`, show them and continue without the question. If the plan ends with `RESULT: REFUSED`, nothing changed. Tell the user each `REFUSED` line. For changes in the worktree, see "Error Handling".

### Step 3: Remove

**Before the first removal attempt, archive anything worth keeping** to a location outside the worktree. Examples are `Notes/` drafts and task artifacts, and the files that the `IGNORED` lines name. A removal can fail halfway: git unregisters the worktree but leaves part of the folder on disk. So do not wait for a failed attempt before you archive.

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" remove <branch-ref> --apply
```

`RESULT: REMOVED` ends this step. Git no longer lists the worktree, and the branch and its commits stay. After a `FAILED` line, each `LEFT` line names what is still there.

**Never use `rm -rf` as a first resort.** On Windows, `Permission denied` on removal is usually not an IDE file lock. Work through this diagnosis in order:

1. **Step 1: shell CWD (the main cause, always first)**. The Bash tool and the PowerShell tool each keep their own current folder (CWD) between calls. An earlier `cd <worktree>` or `Set-Location <worktree>` can leave it inside the worktree, also through a build or test run. Windows then treats the folder as in use. Git or `Remove-Item` reports this as `Permission denied`, with no IDE involved. Move the CWD of both shells out first:

   ```bash
   cd <repo-root>              # Bash
   ```

   ```powershell
   Set-Location <repo-root>    # PowerShell
   ```

   Then run the `remove <branch-ref> --apply` command of the script again. If a folder remains, run a plain `Remove-Item -Recurse -Force <path>` (or `rm -rf <path>`). For a worktree path of short or medium length, this step alone is enough.

2. **Step 2: long path (use it only after Step 1 failed)**. The worktree path plus a deep source tree often exceeds the Windows `MAX_PATH` limit of 260 characters. This also shows as `Permission denied`. You can try the PowerShell extended-path literal first:

   ```powershell
   Remove-Item -LiteralPath '\\?\<absolute-worktree-path>' -Recurse -Force
   ```

   The sandbox of the session can block the `\\?\` literal. If it is blocked or rejected, go to Step 3 at once.

3. **Step 3: leaf-first manual walkup (the reliable fallback)**. Delete the deepest files and folders first, and work up to the worktree root, for example with repeated `rmdir` or `Remove-Item` calls. No single call then needs the full long path. So this step also works without Step 2.

The worktree path is the full branch ref. If long paths cause this error often, suggest shorter branch names to the user. Never shorten the path or the ref yourself (Workflow A).

Tell the user which step fixed the error. Do not force a removal past a real refusal for uncommitted changes.

---

## Workflow D: Removing All Worktrees

**Never remove the main worktree**.

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
   - **Other platforms:** use the equivalent task-provider MCP server. If no MCP tool is available for the platform, **stop and ask the user** for the PR status for that specific worktree.

3. **Apply the merged filter**. If the PR status that you read does not say that the PR is merged, the worktree is not eligible for removal. Any other status (open, draft, closed without a merge, or no PR found) means that you must not remove the worktree automatically.

4. **If discovery fails or is ambiguous**, **stop and ask the user** about that specific worktree: its PR status, or whether to remove it. Examples: MCP is not available, several PRs come back for the same source branch, or no PR comes back but the branch looks active. Do not guess or silently skip. With `--autonomous`, do not stop: keep that worktree, and name it in the final report.

Worktrees with open or undiscoverable PRs must not be removed.

### Step 3: Show list and ask for confirmation

```text
Found the following merged-PR worktrees eligible for removal:
  - .claude/worktrees/feature/tasks/1370383-foo  (branch: feature/tasks/1370383-foo)

The following worktrees have open/active PRs and will be kept:
  - .claude/worktrees/bugfix/1250312-bar

The main worktree will be preserved.

Proceed with removing the 1 eligible worktree? (yes/no)
```

Without `--autonomous`, **stop and wait for an explicit yes.** With `--autonomous`, show the list and continue.

### Step 4: Remove each eligible worktree

For each path, first archive anything worth keeping, as Workflow C Step 3 says. Whoever runs this workflow also removes each eligible path itself. The Rule 7 note of Workflow C applies to each path here too, not only to the removal of a single worktree.

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" remove <branch-ref-1> --apply
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" remove <branch-ref-2> --apply
# ...
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" prune --apply
```

A removal that ends with `RESULT: REFUSED` or `RESULT: FAILED` keeps that worktree. Name it in the report. The prune removes only the git data of a worktree whose folder is gone. If the prune refuses an entry outside `.claude/worktrees/`, name the entry in the report, and leave it.

---

## Lifecycle Rule: Keep Until PR Is Merged

**Do not remove a worktree at the end of a session, at the end of a pipeline, or after the question "are we done?"**.

PR review feedback, follow-up fixes, and build and test runs at the branch HEAD all need the worktree.

You can remove a worktree in two cases. First, the PR is merged, by the rule of the provider (GitHub: `merged: true`, or `state: closed` with `merged_at` set). Second, the user explicitly asks to remove a specific worktree (see Workflow C). Before each removal, read the PR status again.

---

## Recreate-If-Missing Fallback

The worktree can be missing despite the lifecycle rule, for example after a manual removal, an IDE prune, or `git worktree prune`. If the branch has an active PR, recreate the worktree before you do any work.

**Before you delete any stub directory,** find out whether its path starts with `.claude/worktrees/`. If it does not, do not use this fallback on that path. Run the removal of the script first, as the block below shows. It removes an entry that git lists but whose folder is missing, with no `--force`. If the script refuses with `git does not list this folder as a worktree`, the folder is an unregistered orphan stub. List its contents. Then ask the user for an explicit yes before you delete it. The path can hold `Notes/` files or other files that you cannot recover, because the whole `.claude/worktrees/` subtree is gitignored. Never silently `rm -rf` a stub directory. With `--autonomous`, do not delete such a folder. List it in the final report.

```bash
python3 -I "${CLAUDE_SKILL_DIR}/scripts/worktree.py" remove <branch-ref> --apply
# A refusal for a folder that git does not list: list the folder and ask the user. Never chain a blind `rm -rf`.
```

Then recreate the worktree at `.claude/worktrees/<branch-ref>` with Workflow A Step 5. If the local branch still exists, the script uses Case B. If only `origin` has the branch, it uses Case C. It also runs all of Workflow A Step 6 (the post-create bootstrap).

Then work in the recreated worktree. Do not work from the main worktree through `git show <branch>:<path>`.

---

## Error Handling

**Worktree path already exists:** Inform the user. Options: remove the existing one, or list with `git worktree list` to investigate.

**Cannot remove main worktree:** The main repo worktree cannot be removed with this skill. Only secondary worktrees under `.claude/worktrees/` can be removed.

**Uncommitted changes in worktree:** The script refuses the removal, and a `CHANGED` line names each change. Ask the user to commit or stash first. With `--autonomous`, keep that worktree, and name it in the final report. Do not suggest `--force` removal without an explicit warning that uncommitted changes will be lost.

**Permission denied on removal:** On Windows, this is usually not an IDE file lock. Work through the ordered diagnosis in Workflow C Step 3. Do not report an IDE lock and stop. Never blind force-remove.
