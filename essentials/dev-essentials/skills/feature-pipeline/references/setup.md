# Setup (Step 0)

The master agent reads this file at Step 0 of `SKILL.md`. It has the project context, the provider contract, and sub-steps 1 to 15 of Step 0. It also has the format of `task-context.md` and a portability check for a new repository.

## Contents

- Project context
- Provider capability contract
- Step 0 sub-steps
- Task context file
- Portability check for a new repository

## Project context

Before any task lookup or worktree creation, resolve a project-context document. It describes the task provider, the commands, and the conventions of the repository. Use the first source that has a field:

1. The explicit context file (preferred, most complete): `<repo-root>/.claude/feature-pipeline-context.md`.
2. The repository `CLAUDE.md` (fallback). Take what you can from `<repo-root>/CLAUDE.md`. Project Overview gives Repository. Build Commands gives Commands. Architecture and General Working Rules give Key Conventions.
3. The user. For each required field that neither source gave, ask one question with the `AskUserQuestion` tool.

This plugin ships a starter file at `${CLAUDE_PLUGIN_ROOT}/skills/feature-pipeline/project-context.template.md`. For a one-time setup, copy it to `<repo-root>/.claude/feature-pipeline-context.md`, and fill in the placeholders.

Required fields. Resolve them before the rest of Step 0, from the file, from `CLAUDE.md`, or from the answers of the user:

- Task Provider: the provider name, the MCP server prefix, and the project identifier
- Worktree: the branch-name template and its allowed variables (only without `--no-worktree`)
- Repository: the repository type (git), the base branch, and the solution or root path
- Commands: build, test, push, and PR. The lint and pre-build commands are optional.
- Key Conventions: the rules of the project that the agents must follow

Optional fields. They do not block the pipeline:

- Guidance Files: repository-relative paths to guidance docs, for example architecture overviews or domain reference docs
- Architecture Docs: repository-relative paths to architecture docs
- Testing Docs
- Artifacts Directory: the repository-relative path for the pipeline artifacts. The default is `tasks`.

Resolution algorithm:

```text
resolved := {}

if exists(<repo-root>/.claude/feature-pipeline-context.md):
    resolved := parse_sections(that file)

if any required field is still missing AND <repo-root>/CLAUDE.md exists:
    derive missing fields from CLAUDE.md sections:
      - Project Overview + Repository Structure  -> Repository
      - Build Commands / Running Tests            -> Commands
      - General Working Rules / Code Style /
        Conventions / Architecture                -> Key Conventions
    (log each derivation so the user can audit it)

for each required field still missing:
    ask user via AskUserQuestion
    store the answer in `resolved` (and, if the explicit context file
    exists, offer to append the answer to it at end of run)

if Task Provider still missing -> STOP the pipeline (cannot fetch the task)
```

The resolved context goes into each stage prompt as the `<project-context>` block ("Stage Launch" in `SKILL.md`). The project-specific values stay readable text in that block. They are not placeholders.

## Provider capability contract

The project context names the task provider and its MCP server prefix. Look at the MCP tools with that prefix, and pick the methods for these capabilities:

- Fetch the task details by ID
- Fetch the task comments by ID (only for a provider with comments)
- Create a task comment by ID
- Fetch the task metadata: the title, the description, the labels, the priority, and the branch metadata (where the provider has them)

If the MCP server cannot give the required capabilities, stop at once. If the MCP server seems unavailable, apply Safeguard 3 of `SKILL.md` first.

## Step 0 sub-steps

With `--dry-run`, Step 0 changes nothing on disk. It creates no worktree and no branch, runs no Pre-build command, and writes no file. Sub-steps 6, 7, 10, 11, and 12 say what to do instead. Sub-step 15 reports the result.

1. Parse `$ARGUMENTS`. The task ID is `$ARGUMENTS[0]`. The flags are `--dry-run`, `--no-worktree`, `--start-from`, `--skip`, `--model-override`, `--commit-mode`, `--interactive`, and `--autonomous`.
2. Resolve the project context with the three sources above (explicit file, then `CLAUDE.md`, then questions to the user). Make sure that every required field has a value.
3. Look at the MCP tools with the prefix from the project context. Pick the methods that give the required provider capabilities.
4. Fetch the task details and the task comments through the MCP server.
5. Resolve the branch name. If the task metadata has an explicit branch name, use it. Else render the branch template from the project context with its allowed variables.
6. Resolve the project root, `{WORKTREE_PATH}`.

   With `--no-worktree`:

   - Set `{WORKTREE_PATH}` to the current working directory (the repository root).
   - Use the current branch as it is. Do NOT create or switch branches.
   - Log: "Running in-place on branch `<current-branch>`".
   - Skip the worktree creation, the branch fetch, and the copy of `settings.local.json`.

   With `--dry-run` (and no `--no-worktree`), resolve the worktree path and the branch. Do not create them, and do not show the announcement below. If the worktree already exists, set `{WORKTREE_PATH}` to it. Else set `{WORKTREE_PATH}` to the current working directory for the read-only sub-steps, and report the planned path in sub-step 15.

   Else (default), create a worktree:

   - The worktree path is `.claude/worktrees/<branch-name>`.
   - If the worktree already exists, skip the creation, and log "resuming existing worktree".
   - If the worktree does not exist yet, tell the user the resolved settings first:

     > I will create a worktree with the following settings:
     >
     > - **Path:** `<repo-root>/.claude/worktrees/<branch-name>/`
     > - **Branch:** `<branch-name>` (new / existing local / existing remote)
     > - **Base:** `<base-branch-from-project-context>`
     >
     > Starting the pipeline authorises this worktree creation. Continuing…

     Then run Workflow A of `dev-essentials:git-worktree-management` **in pipeline mode**. Pass the resolved path and branch explicitly. Say that the user already approved the worktree with the start of the pipeline. So the approval prompt of Workflow A Step 3 is already answered and must not block. Workflow A does the full bootstrap. It fetches the base branch. It runs `git worktree add` with the right case (A, B, or C) for a new branch, a local branch, or a remote-only branch. It unsets the upstream (`git branch --unset-upstream`), copies `.claude/settings.local.json` into the worktree, and creates `Notes/`. Do NOT do these steps inline. Run Workflow A, so that the full bootstrap runs every time. An ad hoc creation skips two of its steps: `--unset-upstream` and `mkdir -p Notes/`.

   After this sub-step, in both modes, every later file operation and every subagent prompt MUST use `{WORKTREE_PATH}` as the project root.
7. If the project context has a Pre-build command, run it in the `{WORKTREE_PATH}` folder. If it fails, stop at once, because the build fails without it. With `--dry-run`, do not run it. Name it in the plan.
8. Search `{WORKTREE_PATH}` for files that mention the task ID. They are the doc candidates.
9. Resolve `{ARTIFACTS_DIR}`. Use the Artifacts Directory value of the project context. If it has none, use `tasks`.
10. Write `{ARTIFACTS_DIR}/<task-id>/task-context.md` with the task metadata, the branch name, and the doc candidates (see "Task context file" below). With `--dry-run`, do not write the file. Keep its content for the plan of sub-step 15.
11. Read `{ARTIFACTS_DIR}/<task-id>/pipeline-state.json` in the worktree, or create it (see `references/checkpoint-protocol.md`). With `--dry-run`, never create the file. If it exists, read it. If the file exists, this run is a resume. Then run the interruption check of `references/checkpoint-protocol.md` right after the load. It runs before sub-step 12 can overwrite `commitMode`. With `--dry-run`, report the result of the check instead of a stop.
12. Resolve `{COMMIT_MODE}`. If this invocation has `--commit-mode`, use it. Else use the `commitMode` value of `pipeline-state.json` from an earlier run. Else use `finalization`. The precedence and the conflict rule are the same as for `--model-override`. A `--commit-mode` on a resume overwrites the recorded `commitMode`, and the resume logs the change. This holds also after a commit-capable stage ran in the old mode. **Exception:** the new value is `finalization`, the recorded value is `per-step`, and at least one commit-capable stage is already in `completed`. Then do NOT log and allow the overwrite. Stop instead, as the mode-change check of `references/checkpoint-protocol.md` says. If the exception does not apply, record the resolved value in `commitMode`. A later resume uses it, unless that invocation passes `--commit-mode` again. With `--dry-run`, report the result instead of a stop, and do not write `commitMode`.
13. Prepare the prompt blocks. They are the resolved project context and `{ARTIFACTS_DIR}/<task-id>/task-context.md`. They are also the three safeguards of "Pipeline Discipline" in `SKILL.md`, and the `<commit-conventions>` block with its cadence line for `{COMMIT_MODE}` (`references/commit-conventions.md`). "Stage Launch" in `SKILL.md` says how each launch uses them.
14. Each launch makes sure that no placeholder is left in its composed prompt ("Stage Launch" step 6 in `SKILL.md`).
15. With `--dry-run`, announce the plan and the provider details. Also announce the branch name, the worktree path (existing or planned), and the Pre-build command that did not run. Also announce the resolved `{COMMIT_MODE}` and the two planned task comments. Then end the run without a stage.

## Task context file

The master agent writes `{ARTIFACTS_DIR}/<task-id>/task-context.md` once, at sub-step 10, after it fetches the task details from the provider. Format:

```markdown
# Task Context

- **Task ID:** TASK-123
- **Provider Record ID:** 12345 (or "none")
- **Title:** <task title>
- **Priority:** <priority or "unknown">
- **Labels:** <JSON array or comma-separated, or "none">
- **URL:** <provider URL or "none">
- **Branch:** <resolved branch name>

## Description

<full task description / body / issue text>

## Attachments

<JSON array of {title, url} objects, or "none">

## Doc Candidates

<JSON array of repo-relative paths to files mentioning the task ID, or []>
```

Use `"none"` for each value that the task provider does not have. The doc candidates come from sub-step 8.

## Portability check for a new repository

Before you say that the pipeline is ready for a new repository, make sure of these facts:

1. One context source resolves: `<repo-root>/.claude/feature-pipeline-context.md`, or a `<repo-root>/CLAUDE.md` with enough content for the required fields.
2. Each required field (see "Project context") has a value, or the user can answer it through `AskUserQuestion`.
3. The branch template uses only the allowed placeholders that the context source lists.
4. The MCP server with the prefix of the task provider gives the required capabilities.
5. No stage prompt hardcodes a project-specific path or command. Such values come from the resolved project context.
6. `SKILL.md` documents each placeholder that a stage prompt uses.

Static checks (run them from the root of the consumer repository):

```bash
# Explicit context file (if present)
cat .claude/feature-pipeline-context.md

# Find any leaked project-specific tokens in the installed plugin's stage prompts
rg --no-heading --line-number '<repo-specific-token-1>|<repo-specific-token-2>|<repo-specific-command>' "$CLAUDE_PLUGIN_ROOT/skills/feature-pipeline/stages"

# List remaining placeholders in the SKILL file and stages
rg --no-heading --line-number '\{[A-Z0-9_]+\}' "$CLAUDE_PLUGIN_ROOT/skills/feature-pipeline"
```
