---
name: git-worktree-management
description: Creates and manages git worktrees for working on tasks. Use when the user requests to create, list, or remove worktrees (e.g., "new worktree for Task 123456", "list my worktrees", "remove all worktrees").
---

# Git Worktree Management Skill

## Purpose
Manages git worktrees in a dedicated `Worktrees` directory for working on specific tasks in isolation. This allows multiple branches to be checked out simultaneously in separate working directories.

## When to Use
- User requests to create a worktree for a task
- User requests to list existing worktrees
- User requests to remove one or more worktrees

## Prerequisites for Creating Worktrees

**CRITICAL: NEVER invent or guess task numbers or descriptions.**

The user MUST explicitly provide:
- A task number (e.g., 123456)
- A task description (e.g., "Adding Config Repository for WebApi service")

**If the user requests a worktree without providing both values, STOP and ask them to provide:**
1. The task number
2. A clear description of the task

## Workflows

### Workflow A: Creating a New Worktree

**Pre-check:** Verify the user has provided both task number and description. If not, ask for them before proceeding.

#### Step 1: Navigate to Repository Root
Before creating the worktree, change to the repository root:

```powershell
cd $(git rev-parse --show-toplevel)
```

#### Step 2: Determine Base Branch
Find the default base branch of the repository:

```powershell
git symbolic-ref refs/remotes/origin/HEAD
```

This typically returns something like `refs/remotes/origin/main` or `refs/remotes/origin/master`. Extract the branch name from this output.

#### Step 3: Create Worktree Directory Path
Construct the worktree path:
- Location: `../Worktrees/` (one level above the repository root)
- Format: `<task-number>-<concise-description>/`
- Example: `../Worktrees/123456-add-config-repository/`

**Naming Rules:**
- Start with the task number
- Follow with a hyphen
- Use lowercase for the description
- Use hyphens to separate words
- Keep it concise but descriptive
- Remove special characters and spaces

#### Step 4: Create Branch Name
Format: `tasks/<task-number>-<concise-description>`
- Example: `tasks/123456-add-config-repository`
- Must match the worktree directory name (without the path)
- Must start with `tasks/` prefix

#### Step 5: Create the Worktree
Execute the git worktree creation command:

```powershell
git worktree add -b <branch-name> <worktree-path> <base-branch>
```

Example:
```powershell
git worktree add -b tasks/123456-add-config-repository ../Worktrees/123456-add-config-repository main
```

#### Step 6: Confirm Success
After creation, construct the full worktree path and provide commands to open it:
- Get the repo root path from Step 1 (e.g., `C:\Projects\<RepoName>`)
- Remove the repository folder name to get parent directory (e.g., `C:\Projects`)
- Append `\Worktrees\<worktree-name>` (e.g., `C:\Projects\Worktrees\123456-add-config-repository`)

#### Step 7: Find Solution File for Rider
Search for the .sln file in the worktree (typically in the `Sources` subdirectory):

```powershell
Get-ChildItem -Path <full-worktree-path> -Filter *.sln -Recurse | Select-Object -First 1 -ExpandProperty FullName
```

Inform the user:
- The worktree location
- The branch name
- Commands to open the worktree (wrapped in ```powershell``` code blocks):
  - In VS Code: `code <full-worktree-path>`
  - In Rider: `rider <path-to-sln-file>` (if .sln file found)

### Workflow B: Listing Existing Worktrees

When the user asks to see their worktrees (e.g., "which worktrees do I have", "list worktrees"):

#### Step 1: Navigate to Repository Root
```powershell
cd $(git rev-parse --show-toplevel)
```

#### Step 2: List All Worktrees
```powershell
git worktree list
```

#### Step 3: Present Results
Display the worktrees in a clear format showing:
- Worktree path
- Branch name
- Commit hash
- Note which one is the main worktree (the repository itself)

### Workflow C: Removing a Single Worktree

When the user asks to remove a specific worktree:

#### Step 1: Verify Worktree Exists
List worktrees and verify the target exists:
```powershell
git worktree list
```

#### Step 2: Remove the Worktree
```powershell
git worktree remove <path>
```

#### Step 3: Confirm Removal
Inform the user the worktree has been removed.

### Workflow D: Removing All Worktrees

When the user asks to remove all worktrees (e.g., "remove all worktrees", "clean up worktrees"):

**CRITICAL: The main worktree (the repository itself) cannot be removed. Only remove secondary worktrees.**

#### Step 1: List All Worktrees
```powershell
git worktree list
```

#### Step 2: Identify Secondary Worktrees
Parse the output to identify which worktrees are NOT the main repository:
- The main worktree is the repository itself - it is NOT located in the `Worktrees` subdirectory
- Secondary worktrees are those located in `../Worktrees/` (or the full path containing `\Worktrees\`)
- Only secondary worktrees can be removed

#### Step 3: Show List and Request Confirmation
Display the list of worktrees that will be removed and ask for explicit confirmation:

```
Found the following worktrees to remove:
- ../Worktrees/123456-add-config-repository (branch: tasks/123456-add-config-repository)
- ../Worktrees/789012-fix-bug (branch: tasks/789012-fix-bug)

The main worktree will be preserved.

Do you want to proceed with removing these worktrees? (yes/no)
```

**STOP and wait for user confirmation. Do NOT proceed without explicit approval.**

#### Step 4: Remove Each Worktree (Only After Confirmation)
If the user confirms, remove each secondary worktree:
```powershell
git worktree remove <path-1>
git worktree remove <path-2>
# ... etc.
```

#### Step 5: Prune and Confirm
Clean up stale references and confirm completion:
```powershell
git worktree prune
```

Inform the user how many worktrees were removed.

## Example Interactions

### Example 1: Creating Worktree (Missing Information)

**User Request:**
"Create a new worktree"

**Agent Response:**
I need more information to create the worktree. Please provide:
1. The task number (e.g., 123456)
2. A description of the task (e.g., "Adding Config Repository for WebApi service")

### Example 2: Creating Worktree (Complete Information)

**User Request:**
"Create a new worktree for Task 123456: Adding Config Repository for WebApi service"

**Agent Actions:**
1. Navigate to repo root: `cd $(git rev-parse --show-toplevel)`
2. Get base branch: `git symbolic-ref refs/remotes/origin/HEAD` → `refs/remotes/origin/main`
3. Parse task number: `123456`
4. Create concise name: `add-config-repository`
5. Construct paths:
   - Worktree: `../Worktrees/123456-add-config-repository/`
   - Branch: `tasks/123456-add-config-repository`
6. Execute: `git worktree add -b tasks/123456-add-config-repository ../Worktrees/123456-add-config-repository main`
7. Find .sln file: `Get-ChildItem -Path C:\Projects\Worktrees\123456-add-config-repository -Filter *.sln -Recurse | Select-Object -First 1 -ExpandProperty FullName` → `C:\Projects\Worktrees\123456-add-config-repository\<path-to>\<RepoSolution>.sln`

**Agent Response:**

Created new worktree at `../Worktrees/123456-add-config-repository/`

Branch: `tasks/123456-add-config-repository`

Based on: `main`

To open this worktree in VS Code:
```powershell
code C:\Projects\Worktrees\123456-add-config-repository
```

To open in Rider:
```powershell
rider C:\Projects\Worktrees\123456-add-config-repository\<path-to>\<RepoSolution>.sln
```

### Example 3: Listing Worktrees

**User Request:**
"Which worktrees do I currently have?"

**Agent Actions:**
1. Navigate to repo root
2. Execute: `git worktree list`
3. Parse output

**Agent Response:**
```
You have the following worktrees:

1. C:\Projects\<RepoName> (main)
   Branch: main
   
2. C:\Projects\Worktrees\123456-add-config-repository
   Branch: tasks/123456-add-config-repository
   
3. C:\Projects\Worktrees\789012-fix-bug
   Branch: tasks/789012-fix-bug
```

### Example 4: Removing All Worktrees

**User Request:**
"Remove all worktrees"

**Agent Actions:**
1. List worktrees with `git worktree list`
2. Identify secondary worktrees (excluding main repo)
3. Present list for confirmation

**Agent Response:**
```
Found the following worktrees to remove:

- C:\Projects\Worktrees\123456-add-config-repository (branch: tasks/123456-add-config-repository)
- C:\Projects\Worktrees\789012-fix-bug (branch: tasks/789012-fix-bug)

The main worktree (C:\Projects\<RepoName>) will be preserved.

Do you want to proceed with removing these 2 worktrees? (yes/no)
```

**User:** "yes"

**Agent Actions:**
1. Execute: `git worktree remove C:\Projects\Worktrees\123456-add-config-repository`
2. Execute: `git worktree remove C:\Projects\Worktrees\789012-fix-bug`
3. Execute: `git worktree prune`

**Agent Response:**
```
Successfully removed 2 worktrees. All secondary worktrees have been cleaned up.
```

## Error Handling

### Worktree Already Exists
If the worktree path already exists, inform the user and suggest:
- Using a different description
- Removing the existing worktree with `git worktree remove <path>`
- Listing existing worktrees with `git worktree list`

### Branch Already Exists
If the branch name already exists, inform the user and suggest:
- Using a different branch name
- Checking out the existing branch
- Deleting the old branch if no longer needed

### Not in a Git Repository
If the command is run outside a git repository, inform the user they need to be in a git repository to manage worktrees.

### Cannot Remove Main Worktree
If the user tries to remove the main worktree, inform them that the main repository worktree cannot be removed. Only secondary worktrees in the `Worktrees` directory can be removed.

### Worktree Has Uncommitted Changes
If a worktree has uncommitted changes, git will refuse to remove it. Inform the user they need to either:
- Commit or stash the changes
- Use `git worktree remove --force <path>` to force removal (warn about data loss)

## Reference: Git Worktree Commands

These commands are used internally by the skill:

```powershell
# List all worktrees
git worktree list

# Add a new worktree
git worktree add -b <branch-name> <path> <base-branch>

# Remove a worktree
git worktree remove <path>

# Force remove a worktree (even with uncommitted changes)
git worktree remove --force <path>

# Clean up stale worktree references
git worktree prune

# Get repository root
git rev-parse --show-toplevel

# Get default branch
git symbolic-ref refs/remotes/origin/HEAD
```
