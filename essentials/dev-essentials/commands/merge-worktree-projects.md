---
description: Merges the Claude Code project folders of git worktrees back into the main project folder of their repo. It moves the sessions, merges the memory files, and deletes the empty folders. Dry run by default. With --apply, it acts only after an explicit yes.
argument-hint: "[<main-project-folder-or-repo-keyword> ...] [--exclude=<substring>[,<substring>...]] [--apply]"
---

# Merge Worktree Projects

## Purpose

Claude Code keeps one project folder for each working folder. The project folders are in the `projects/` folder under the Claude config root. The config root is the folder in the `CLAUDE_CONFIG_DIR` environment variable. If that variable is not set, the config root is `<home>/.claude`. The name of a project folder comes from the absolute path of its working folder, with the drive letter and the path segments. Each separator becomes `-`.

A git worktree has a different path than the main checkout of its repo, usually `<repo-root>/.claude/worktrees/<branch>/...` (see `dev-essentials:git-worktree-management`). So each worktree that you worked in gets its **own separate project folder**, although it belongs to the same repo. Over time, the sessions and the memory of one repo spread across these folders.

This command merges those worktree folders back into the one main project folder. It does this for each project that `$ARGUMENTS` names. If `$ARGUMENTS` names no project, it does this for **every** project that has worktree folders. Then it deletes the empty worktree folders. **By default, this is a dry-run report only**. Nothing is written or deleted before two things happen: `--apply` is passed, and the user explicitly confirms the exact deletion list. See "Modes and safety gate" below.

## What this touches

- Only folders in the `projects/` folder under the Claude config root (resolved as described above). These folders hold the session transcripts and the memory of Claude Code. Nothing else.
- It never reads or writes anything inside a git repository, its `.git` folder, or a `.claude/worktrees/` checkout. These are in a different place on disk than the `projects/` folder, and this command does not walk them.

## Inputs (`$ARGUMENTS`)

- **Main project folder names (optional).** Zero or more of these: a distinct keyword or substring (for example a repo name), or an exact folder name. Each one names the main folder that a match group merges INTO. To resolve a keyword, list the `projects/` folder under the resolved config root, and match without regard to case. The main folder is the one **without** a `--claude-worktrees-` (or `--worktrees-`) segment in its name. If a keyword matches more than one candidate main folder, stop and ask which one to use. Do not guess.
- **No main folder name.** Then process **all** projects. Each folder in `projects/` whose name does NOT contain `--claude-worktrees-` or `--worktrees-` is a candidate main folder. Run Steps 1 to 6 for each candidate that has at least one worktree sibling. Skip a candidate with no sibling silently. Do not report a no-op for every unrelated project.
- **`--exclude=<substring>[,<substring>...]` (optional).** Folder names or substrings to skip for this run, for example because sessions are active there. The flag applies both to a single project and to "process all". Leave an excluded folder completely untouched. Do not even inspect it for collisions. Name it as skipped in the final report.
- **Free text**. The user can name a folder to skip in free text instead of the flag. Example: "do not touch X, there are active sessions there". Treat that like `--exclude=X`. In the same way, a free-text instruction to run the merge (for example "yes, go ahead and merge them") counts as `--apply`.
- **`--apply` (optional, off by default).** Without it, the command always runs as a dry run. Steps 1 to 3 (discovery, safety check, collision check) run in full. Steps 4 and 5 only *compute* the plan for the merge and the deletions. No file is moved, merged, or deleted. With `--apply`, the command computes and shows the same plan. Then the user must pass the explicit confirmation gate below before Steps 4 and 5 run.

## Modes and safety gate

- **Default (no `--apply`): dry run.** Run every step below exactly as written. But Steps 4 and 5 only *compute* their result, and they make no write and no deletion. The result names the rename map and the memory files that an applied run creates, appends to, or skips. It also names the top-level entries that the run moves, and the folders that end up empty and that it deletes. Start the report of Step 6 with `DRY RUN — no files were moved, merged, or deleted.` End the report with "Re-run with `--apply` to execute this exact plan."
- **`--apply`: execute, after confirmation.** Run Steps 1 to 3 as usual. They only read, in every mode. Then compute the plan of Steps 4 and 5 exactly as the dry run does. Before you write or delete anything, show the user that plan and one explicit line: "About to delete: `<folder>`, `<folder>`, …". If every pair was skipped or STOPped, the line is "Nothing to delete". Ask for confirmation with the **AskUserQuestion** tool (proceed with exactly this plan: yes/no). On any answer other than an explicit "yes", stop with nothing changed. Steps 4 and 5 run only after an explicit "yes". Then Step 6 reports the real result.

## Step 1 — Discover the merge group for each main folder

Do this for each resolved main folder name `M`. In "process all" mode, that is every candidate found above.

1. Use the `projects/` listing of the discovery, where one exists. In exact-folder-name mode, no listing exists yet, so list the folder now. List it at most once per run, not once for each `M`.
2. A folder `W` is a **worktree sibling** of `M` in one case only. Its name equals the name of `M` followed directly by `--claude-worktrees-<anything>` or `--worktrees-<anything>`. Ignore the case of the leading drive-letter segment (for example `D--` and `d--`). Do not match on loose substring similarity. Require this exact prefix relation, so that an unrelated project that only shares a path segment never merges in by mistake.
3. Drop each `W` that the `--exclude=` list matches.
4. If `M` has no worktree sibling, say so and go on. This is not an error.

## Step 2 — Safety check before touching anything

For each remaining `(M, W)` pair:

- Look at the modification time of every file and folder inside `W`. Go into subfolders too, so that subagent transcripts count. If anything changed in about the last 2 hours, treat `W` as **possibly active**, and do not merge it. List it in the report as "skipped — recent activity, confirm it's safe to merge", and ask explicitly before you try it again.
- Also treat the folder of the **currently running session** as active. Never merge or delete it, even for an argument that matches it.
- Treat every other pair as safe to merge without more confirmation. Do not ask for permission for each folder. Report what you did afterward.

## Step 3 — Collision check (per pair, before moving anything)

For each `(M, W)` pair, before you move or delete anything:

1. List the top-level entries of `W`: the session files `<uuid>.jsonl`, the subagent-transcript folders `<uuid>/`, and the top-level `MEMORY.md` of `W`, where one exists.
2. For each entry of step 1, check whether `M` has an entry with the same name:
   - A `.jsonl` file or a `<uuid>/` folder with the same name: session UUIDs are unique in practice, so this case is not expected. If it happens, STOP for this pair. Do not move or delete anything in it. Report the exact colliding names for a manual fix.
   - `MEMORY.md` with the same name: this is not a collision. Step 4 handles `MEMORY.md` on its own. Step 5 excludes it on purpose from its "move every remaining top-level entry".
3. A `memory/` subfolder of `W` is not part of this step. Step 4 handles the collisions of each file in it.

## Step 4 — Merge `memory/`, if `W` has a `memory/` folder or a top-level `MEMORY.md`

Every run computes this step. Only an `--apply` run with an explicit "yes" writes it (see "Modes and safety gate" above). In a dry run, do every check below (they all only read), and record what each part is to do instead of doing it.

Most worktree folders have neither of the two, because memory usually grows only in the main folder. If `W` has a `memory/` folder OR a top-level `MEMORY.md`, run this merge for the pair. The top-level case covers a `W` that grew only a top-level index.

1. Start an empty rename map (`originalName -> finalName`) for this pair.
2. For each fact file in the memory folder of `W`:
   - If the memory folder of `M` has no file with that name, move the file as it is. Then `finalName == originalName`, and the rename map gets no entry.
   - If the names match and the two files are byte-identical, keep the copy of `M`, and drop the duplicate of `W` (`finalName == originalName`). Never silently overwrite.
   - If the names match and the contents differ, try `<name>-2.md`, `<name>-3.md`, and so on in the memory folder of `M`. Move the file of `W` in under the first name that does not exist there yet. Never write `<name>-2.md` blindly, because it can already exist.
     - If no free name exists up to `<name>-9.md`, STOP for this file. Do not move or delete anything for it. Leave `W/memory/` in place with the STOPped files. For this pair, exclude `W/memory/` from the move of Step 5, and from the empty check and the deletion of Step 5. Flag the pair as **partially retained** in the final report, together with the STOPped file.
     - Otherwise, record `originalName.md -> <chosen-filename>` in the rename map. Use the exact filename. It already has its extension, so do not add `.md` again. Flag the file in the final report as one that needs a manual merge or review.
3. Resolve the `MEMORY.md` path of each side on its own. `W` and `M` do not have to share a layout. For example, `W` can have only a top-level copy while `M` has one under `memory/`, or the other way around.
   - For `W`: use `W/memory/MEMORY.md`. If that file does not exist, use `W/MEMORY.md`. If neither file exists, `W` has no index to merge.
   - For `M`: use `M/memory/MEMORY.md`. If that file does not exist, use `M/MEMORY.md`. If neither file exists, `M` has no index.
   - The nested path under `memory/` is the common case. The top-level path is only a fallback.
4. If step 3 found an index for `W`:
   - If `M` also has an index, merge the index of `W` into it, and never overwrite the copy of `M`. Take each pointer line of the `W` copy whose linked filename the `M` copy does not reference yet. If the line names an `originalName` that the rename map renamed, replace it with the `finalName`. Then append the line to the copy of `M`. Do not append a pointer line whose target file was a STOP case of step 2. If a pointer line was such a STOP case, keep the index of `W` in place for this pair. Skip step 4.5 for it (keep the `W` index). Only a pair with a STOP case keeps its `W` index. Name the line in the final report under the partially retained pair. List the appended lines (after the rewrite) in the final report.
   - If `M` has no index, create one at the nested path `M/memory/MEMORY.md` (the common case of step 3) from the copy of `W`. First rewrite the filename of each pointer line through the rename map of step 2. One exception: a pointer line whose target file was a STOP case of step 2 (no free name). That file did not move. So leave the filename of that line as it is, and add a note to the line, for example "⚠ not migrated, see manual resolution". Do not skip this step because `M` had no index. A pair that keeps its `W` index is the exception (the merge branch above). For every other pair, step 4.5 deletes the copy of `W`. So an index of `W` that is not merged is lost. List the created file and its content (after the rewrite) in the final report.
5. Remove the `MEMORY.md` or `memory/MEMORY.md` copy of `W`. It is now merged or moved.
6. When every file under `W/memory/` is merged into `M/memory/` and the `MEMORY.md` copy of `W` is gone, delete the empty `W/memory/` folder. Do it at once, before Step 5 runs. Step 5 works on what remains at the top level of `W`, and it must not see `memory/` there.

## Step 5 — Migrate and clean up

Every run computes this step. Only an `--apply` run with an explicit "yes" performs it. In a dry run, record what is to move and which folders are to end up empty and so eligible for deletion. Do not move or delete anything.

This step skips two kinds of pair. Step 2 skipped the first kind in full (recent activity). Step 3 STOPped the second kind in full (a session-name collision for the whole pair). Every other pair goes through this step, also a pair that Step 4.2 flagged as partially retained.

1. Move (do not copy) every remaining top-level entry from `W` into `M`. Do not touch what Step 4 already handled: a `memory/` folder or a top-level `MEMORY.md`. Step 4 either merged and removed it, or left it in place on purpose (for a STOP case of one file).
2. Check whether `W` is now empty.
3. If `W` is NOT empty, do NOT delete it. Report exactly what is left and why, and stop here for this pair.
4. If `W` is empty, delete the `W` folder.

## Step 6 — Report

Give these facts for each main project:

- The number of merged worktree folders.
- The total number of moved session files and folders.
- Each memory file that needs a manual review after a collision.
- Each pair that Step 2 skipped for recent activity.
- Each excluded folder.

Say clearly whether this was a **dry run** (nothing changed, see "Modes and safety gate") or an **applied** run (the run executed the confirmed plan). Keep the report short. It is a routine maintenance report.

## Hard rules

- Never write or delete anything without both of these: `--apply`, and an explicit "yes" at the deletion-list confirmation of "Modes and safety gate". The default is always a dry run.
- Never touch a folder that `--exclude=` matches, or that a "do not touch, active sessions" note names.
- Never delete a folder that is not fully empty after the migration.
- Never overwrite an existing file in the main folder. Merge or rename instead, and flag it.
- Move or rename the entries. Do not copy and delete them. The only case for a copy is a move across drives.
