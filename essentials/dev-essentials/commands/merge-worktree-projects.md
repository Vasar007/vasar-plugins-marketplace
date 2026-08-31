---
description: Consolidate Claude Code project folders under the Claude config root's projects/ directory that the harness split off for git worktrees back into their main project folder — migrating sessions and memory, then deleting the emptied worktree folders. Defaults to a dry-run report; pass --apply and confirm the exact deletion list before anything is written or deleted. Safe by default — skips any folder with recent activity or explicitly excluded, and never overwrites memory files, it merges them.
argument-hint: "[<main-project-folder-or-repo-keyword> ...] [--exclude=<substring>[,<substring>...]] [--apply]"
---

# Merge Worktree Projects

## Purpose

Claude Code names each project folder under the Claude config root's
`projects/` directory (resolve the config root from the `CLAUDE_CONFIG_DIR`
environment variable if it is set, else `<home>/.claude`) by sanitizing the
absolute working-directory path (drive letter + path segments, separators
replaced with `-`). A git worktree checkout lives at a different filesystem
path than its main repo checkout (typically
`<repo-root>/.claude/worktrees/<branch>/...`, per
`dev-essentials:git-worktree-management`), so every worktree worked in gets
its **own separate project folder** — even though it is logically the same
repo/project, which scatters sessions and memory over time.

This command folds those worktree-derived folders back into the one
canonical "main" project folder — for the project(s) named in `$ARGUMENTS`,
or for **every** project that has any, if none is named — then removes the
emptied worktree folders. **By default this is a dry-run report only** —
nothing is written or deleted until `--apply` is passed and the exact
deletion list has been explicitly confirmed (see "Modes and safety gate"
below).

## What this touches

- Only folders under the Claude config root's `projects/` directory (the
  config root resolved as described above) — the agent harness's own
  session-transcript and memory bookkeeping. Nothing else.
- It never reads or writes anything inside an actual git repository, its
  `.git` directory, or a `.claude/worktrees/` checkout — those are a
  different filesystem location entirely from the harness's `projects/`
  folder, and this command does not walk them.

## Inputs (`$ARGUMENTS`)

- **Main project folder name(s) — optional.** Zero or more of: a distinctive
  keyword/substring (e.g. a repo name) or an exact folder name — the
  canonical folder each match group should be merged INTO. Resolve a keyword
  to the exact folder name by listing the `projects/` directory under the
  resolved config root and matching case-insensitively; the main folder is
  the one **without** a `--claude-worktrees-` (or `--worktrees-`) segment in
  its name. If a keyword matches more than one candidate main folder
  (ambiguous), stop and ask which one to use — do not guess.
- **If no main-folder name is given at all**, process **all** projects: treat
  every folder under the `projects/` directory that does NOT contain
  `--claude-worktrees-`/`--worktrees-` in its name as a candidate main
  folder, and run Steps 1–6 for each one that actually has at least one
  worktree sibling (silently skip candidates with none — don't report a
  no-op for every unrelated project).
- Optional `--exclude=<substring>[,<substring>...]` — folder names (or
  substrings) to skip entirely for this run, e.g. because there are active
  sessions there. Applies in both single-project and "process all" mode.
  Leave excluded folders completely untouched — not even inspected for
  collisions — and mention them as skipped in the final report.
- If a project is named this way in free text instead of the flag syntax
  (e.g. "don't touch X, there are active sessions there"), treat that the
  same as `--exclude=X`. Likewise, a free-text instruction to actually run
  the merge (e.g. "yes, go ahead and merge them") counts as `--apply`.
- **`--apply`** — optional, off by default. Without it, this command always
  runs as a dry run: Steps 1–3 (discovery, safety check, collision check)
  run in full, and Steps 4–5 only *compute* the merge/delete plan — no file
  is moved, merged, or deleted. With `--apply`, the same plan is computed and
  shown, then the explicit confirmation gate below must be passed before
  Steps 4–5 actually execute.

## Modes and safety gate

- **Default (no `--apply`) — dry run.** Run every step below exactly as
  written, but Steps 4 and 5 only *compute* their outcome — the rename map,
  which memory files would be created/appended/skipped, which top-level
  entries would move, which folders would end up empty and therefore
  deleted — without making any write or delete. Step 6's report is prefixed
  `DRY RUN — no files were moved, merged, or deleted.` and ends with:
  "Re-run with `--apply` to execute this exact plan."
- **`--apply` — execute, after confirmation.** Run Steps 1–3 as normal
  (read-only regardless of mode), then compute Steps 4–5's plan exactly as
  the dry run does. Before writing or deleting anything, show the user that
  same computed plan plus an explicit line — "About to delete: `<folder>`,
  `<folder>`, …" (or "Nothing to delete" if every pair was skipped or
  STOPped) — and ask for confirmation via the **AskUserQuestion** tool
  (proceed with exactly this plan: yes/no). On anything other than an
  explicit "yes", stop here with nothing changed. Only after an explicit
  "yes" do Steps 4 and 5 actually execute and Step 6 reports the real
  outcome.

## Step 1 — Discover the merge group for each main folder

For each resolved main folder name `M` (every candidate found above, when
running in "process all" mode):

1. Reuse the `projects/` listing already fetched during discovery, or list
   the directory now if there is none (exact-folder-name mode). Either way,
   list it at most once per run, not once per `M`.
2. A folder `W` is a **worktree sibling** of `M` if, ignoring the case of the
   leading drive-letter segment (e.g. `D--` vs `d--`), `W`'s name equals `M`'s
   name followed immediately by `--claude-worktrees-<anything>` or
   `--worktrees-<anything>`. Do not match on loose substring similarity —
   require this exact prefix relationship, so an unrelated project that
   merely shares a common path segment is never accidentally merged in.
3. Drop any `W` matched by the `--exclude=` list.
4. If no worktree siblings are found for `M`, say so and move on — this is
   not an error.

## Step 2 — Safety check before touching anything

For every remaining `(M, W)` pair:

- Inspect the modification time of every file/dir inside `W` (recursively for
  subagent transcripts). If anything was modified in roughly the last 2
  hours, treat `W` as **possibly active** — do not merge it. List it in the
  report as "skipped — recent activity, confirm it's safe to merge" and ask
  explicitly before retrying.
- Also treat the folder of the **currently running session** as active and
  never merge or delete it, even if the argument list would otherwise match
  it.
- Everything else is presumed safe to merge without further confirmation —
  don't ask permission per-folder, just report what was done afterward.

## Step 3 — Collision check (per pair, before moving anything)

For each `(M, W)` pair, before moving or deleting anything:

1. List `W`'s top-level entries: session `<uuid>.jsonl` files, `<uuid>/`
   subagent-transcript directories, and a top-level `MEMORY.md` if present.
2. For each entry from step 1, check whether an entry of the same name
   exists in `M`:
   - `.jsonl` file or `<uuid>/` directory name match: session UUIDs are
     effectively unique, so this should not occur. If it does, STOP for
     this pair — do not move or delete anything in it — and report the
     exact colliding name(s) for manual resolution.
   - `MEMORY.md` name match: not a collision. Leave it for Step 4's
     dedicated `MEMORY.md` handling — it is deliberately excluded from
     Step 5's blanket "move every remaining top-level entry".
3. A `memory/` subfolder, if `W` has one, is not checked here — its
   per-file collisions are handled inside Step 4.

## Step 4 — Merge `memory/`, if `W` has a `memory/` folder or a top-level `MEMORY.md`

Computed on every run; only actually written when `--apply` is set and
confirmed (see "Modes and safety gate" above) — in a dry run, perform every
check below (all reads) and record what each part *would* do instead of
doing it.

Most worktree folders will have neither — memory usually only accumulates in
the main folder. If `W` has a `memory/` folder OR a top-level `MEMORY.md`
(the latter covers a `W` that grew only a top-level index), run this per-pair
merge:

1. Initialize an empty rename map (`originalName -> finalName`) for this
   pair.
2. For each fact file in `W`'s memory dir:
   - If no file of that name exists in `M`'s memory dir: move it as-is
     (`finalName == originalName`; no rename-map entry needed).
   - Else if the two files are byte-identical: keep `M`'s copy, drop `W`'s
     duplicate (`finalName == originalName` — never silently overwrite).
   - Else (names collide, contents differ): probe `<name>-2.md`,
     `<name>-3.md`, … in `M`'s memory dir and move `W`'s file in under the
     first name that doesn't already exist there — never blindly write
     `<name>-2.md`, which may already exist. If no free name is found up to
     `<name>-9.md`, STOP for this file — do not move or delete anything for
     it: leave `W/memory/` in place (holding the STOPped file(s)), exclude
     `W/memory/` from Step 5's move and from Step 5's
     empty-check/deletion for this pair, and flag the pair as **partially
     retained** in the final report alongside the STOPped file. Otherwise,
     record `originalName.md -> <chosen-filename>` in the rename map (the
     exact filename used — it already carries its extension, so do not
     append `.md` again) and flag it in the final report as needing manual
     merge/review.
3. Resolve each side's `MEMORY.md` path independently — `W` and `M` are not
   assumed to share a layout (e.g. `W` may only have a top-level copy while
   `M` nests one under `memory/`, or vice versa):
   - For `W`: use `W/memory/MEMORY.md` if it exists; else `W/MEMORY.md` if
     it exists; else `W` has no index to merge.
   - For `M`: use `M/memory/MEMORY.md` if it exists; else `M/MEMORY.md` if
     it exists; else `M` has no index.
   - The nested `memory/`-relative path is the common case (5 of 6 real
     on-disk project folders nest it there); top-level is only a fallback.
4. If `W` resolved to an existing index in step 3:
   - If `M` also has an index: merge `W`'s into `M`'s without ever
     overwriting `M`'s copy — for each pointer line in `W`'s copy whose
     linked filename isn't already referenced in `M`'s copy, rewrite that
     filename through the rename map from step 2 (substitute the
     `finalName` if the line names an `originalName` that was renamed),
     then append the rewritten line to `M`'s copy. List the appended lines
     (post-rewrite) in the final report.
   - If `M` has no index (nothing to append into): create `M`'s index at
     the canonical nested path (`M/memory/MEMORY.md`, per the "5 of 6"
     convention in step 3) from `W`'s copy, rewriting every pointer line's
     filename through the rename map from step 2 first — except a pointer
     line whose target file was a per-file STOP casualty (step 2's
     no-free-name case): that file was never actually migrated, so leave
     that line's filename unrewritten and annotate it inline (e.g. "⚠ not
     migrated — see manual resolution") instead of rewriting it as if the
     file had moved normally. Do not skip this step just because `M` had
     nothing to merge into — step 5 deletes `W`'s copy regardless, so an
     unmerged `W` index would otherwise be lost entirely. List the created
     file and its (post-rewrite) contents in the final report.
5. Remove `W`'s `MEMORY.md`/`memory/MEMORY.md` copy (now merged or moved).
6. Once every file under `W/memory/` has been merged into `M/memory/` and
   `W`'s `MEMORY.md` copy is gone, delete the now-empty `W/memory/` folder
   immediately, before Step 5 runs — Step 5 operates on whatever remains at
   `W`'s top level and must not see `memory/` there.

## Step 5 — Migrate and clean up

Computed on every run; only actually performed when `--apply` is set and
confirmed — in a dry run, record what would move and which folders would end
up empty and therefore eligible for deletion, without moving or deleting
anything.

Runs for each pair not fully skipped by Step 2 (recent activity) or fully
STOPped by Step 3 (whole-pair session-name collision) — including a pair
Step 4.2 flagged as partially retained.

1. Move (not copy) every remaining top-level entry from `W` into `M`, except
   anything Step 4 already handled: a `memory/` folder or top-level
   `MEMORY.md` was either merged and removed there, or (for a per-file STOP
   casualty) deliberately left in place. Either way, do not touch it here.
2. Verify `W` is now empty.
3. If `W` is still NOT empty after the move, do NOT delete it — report
   exactly what's left and why, and stop here for this pair.
4. If `W` is empty, delete the `W` folder.

## Step 6 — Report

Summarize per main project: how many worktree folders were merged, how many
session files/dirs moved in total, any memory-collision files needing manual
review, any pairs skipped for recent activity, and any folders explicitly
excluded. State plainly whether this was a **dry run** (nothing changed —
see "Modes and safety gate") or an **applied** run (the confirmed plan was
executed). Keep it concise — this is a routine maintenance report, not a
deep-dive.

## Hard rules

- Never write or delete anything without `--apply` having been passed AND
  the deletion-list confirmation from "Modes and safety gate" having been
  explicitly answered "yes" — the default is always a dry run.
- Never touch a folder matched by `--exclude=` or by name in a "don't touch,
  active sessions" note.
- Never delete a folder that isn't fully empty after migration.
- Never overwrite an existing file in the main folder — merge or rename
  instead, and flag it.
- Prefer move/rename over copy+delete for the actual migration; only fall
  back to copy if moving across drives is ever needed.
