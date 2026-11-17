# Orchestrated Review Mode — Context-Budget-Preserving Reviewer Dispatch

Phase 3 of `SKILL.md` uses this file. It is a **different way to run Phase 3 only**, for targets that are too large for the context of one reviewer. It does not replace the default dispatch of one reviewer or of parallel reviewers. That dispatch stays the default for every target below the threshold. If Phase 3 chooses this mode, read this file. Else use `references/reviewer-briefs.md` as normal.

## Contents

- When to use this mode
- What this mode dispatches (not how: see cross-reference below)
- Role 1: Target Explorer
- Check the areas between Role 1 and Role 2
- Role 2: Area Explorers (parallel, one per area)
- Step between Role 2 and Role 3: collate
- Role 3: Main-agent synthesis (not a subagent)

The shape works for any large `branch`, `pr`, `diff`, or `commits` target of this skill.

---

## When to use this mode

Use this mode for a target that is too large to read in full. Such a read of the diff or of all changed files fills the context that the orchestrator needs for Phases 4 to 9. The mode also fits a target where `--reviewer-focus` alone does not reduce the reading enough.

- **Diff or target size over about 2,000 lines, or over about 30 changed files**: this mode is a reasonable choice.
- **Below that threshold**: stay on the default Phase 3 flow. That flow is one reviewer, or a parallel pair or quad, with the full diff in the brief of `references/reviewer-briefs.md`. This mode adds dispatch overhead, and a small or medium target does not need it.

The threshold calls for judgment. It is not a fixed gate. A target just under it can still need this mode, for example a target spread over many small files in unrelated areas. A target just over it can still do without this mode, for example a target in one file. State the choice and the reason in the Brief format of the cycle.

## What this mode dispatches (not how — see cross-reference below)

This file defines **roles and prompt shapes**: what each subagent does and what it returns. It does not repeat the **dispatch mechanics**, which `dev-essentials:subagent-orchestration` covers. An example is several independent `Agent` calls in one message, against calls in sequence. Follow that skill to launch these subagents. The roles below say which subagents to dispatch, and in which order.

Three roles, in this order of dependency:

1. **Target Explorer** (always): one subagent. It builds a fact map of the target, with no judgment.
2. **Area Explorers** (always, after the Target Explorer returns): one subagent for each logical area, all dispatched together. They do not depend on each other.
3. **Main-agent synthesis** (not a subagent): the orchestrator collects the results into the reviewer report format that Phase 3 always produces. Then Phase 4 continues with no change.

Models: dispatch the Area Explorers on `--reviewer-model`, because they judge code. A command with no `--reviewer-model` dispatches them on the model of the session. Dispatch the Target Explorer as `general-purpose` with `model: "haiku"` and `effort: "low"`, because it only maps facts. In `dev-essentials:review-loop`, also pass `--reviewer-effort` to the Area Explorers.

The orchestrator never reads the full diff or full files itself. It reads only the fact map of the Target Explorer and the structured findings of the Area Explorers. At the very end, it reads the lines that the findings point to.

---

## Role 1 — Target Explorer

One subagent, dispatched alone, because Role 2 needs its map. It returns a fact map with no judgment and no raw diff or file contents, as the template below says.

The map has a cap of 150 lines in total. If the map is too long, the Target Explorer cuts in this order: Links first, then Symbols, then Signatures, then Tests. It never cuts Ranges. It records every cut under "Not mapped".

Before the dispatch, the orchestrator groups the changed files into areas with the script `group_diff.py` of the review-loop skill. The caller names `{REVIEW_LOOP_DIR}`, the folder of that skill. The script needs Python 3 and git. On Windows, run it in the Bash tool (Git Bash):

```bash
python3 -I "{REVIEW_LOOP_DIR}/scripts/group_diff.py" --repo "<repository root>" --range "<diff range>"
```

The script lists each changed file in exactly one area, so no file drops out of the review. Its output has a `TOTAL` line, and an `AREA` line and the file lines of each area. Put the whole output into the prompt in place of `<AREAS>`. If `python3` is not available or the script exits with code 2, do not use this mode. Use the default flow of the caller, and say why in the report.

Use the model and the effort of the Models paragraph above. It needs Bash for `git diff`, so it is not `dev-essentials:code-locator`, which has no Bash. The agent reads the diff in parts, because this dispatch has no auto-compact window. This is an accepted trade-off.

Prompt template:

```text
You are building a fact map of a large review target. A reviewer will read the map to decide where
to look, so the reviewer does not have to read everything. You map. You do not review.

Target: <branch diff origin/<base>...HEAD | PR <id> via GitHub MCP | commit range | file set>
<Include exactly what Phase 1 already resolved: branch/PR refs, or the file list, per the
target's resolution row in SKILL.md Phase 1. Do not ask the subagent to re-resolve the target.>

Also resolve, alongside the diff range above, a **source tree-ish** — a single ref usable with
`git show <tree-ish>:<path>` (a diff range like `A...B` is not valid there). Resolution by target:

- `target=branch` → `HEAD`.
- `target=pr <id>` → `origin/pull/<id>/head` (the head ref of the PR that SKILL.md Phase 1
  fetched for the diff).
- `target=commits <N>` → `HEAD`.
- `target=diff <range>` → the range's right-hand endpoint (`HEAD` when the range has no explicit
  right side).

Report it separately from the diff range — the two are never interchangeable.

Hard rules:
- State facts only. Each fact carries `path:line` evidence.
- Do not write severity, risk words, opinions, suggestions, or words like "looks wrong".
- Do not rank files by importance. Do not guess the intent of a change.
- If a fact needs a judgment to state, leave it out, or put it under "Not mapped".
- Run `git diff --stat` first. Then run `git diff -U0` for one area or one file at a time, and use
  Grep. Never run one `git diff -U0` for the whole target. Read only the lines that you need.
- Do not copy diff text or file contents into the map. Write names, numbers, and `path:line`.
  The one exception is a signature line in Signatures. Write each one as at most one line
  (about 120 characters, cut with "..." if longer).
- Do not read the diff of a file in the area "skipped". It is a lock file or a generated file.

Areas, from the script group_diff.py. Map the files area by area. Do not regroup them:
<AREAS>

Tasks:
1. <If target=pr: call `pull_request_read` per `dev-essentials:github-mcp-conventions` (explicit
   `owner` and `repo` on the call).>
2. Run: git diff --stat <range>; git log --oneline <range>. Then run
   git diff -U0 <range> -- <path> for one area or one file at a time. For a renamed file, pass
   the old and the new path: git diff -U0 <range> -- <old> <new>. Then rename detection still works.
3. Use Grep to find the links between the changed files.

Report the map in these sections, in this order, and NOTHING else. The map has a cap of 150
lines in total. If you must cut, cut Links first, then Symbols, then Signatures, then Tests.
Never cut Ranges. Record every cut under "Not mapped".
1. Target: identity (branch, PR, or commit range), a one-line title if available, and the
   number of commits.
2. Ranges: the resolved **diff range** (for `git diff` and `git log`) AND the resolved **source
   tree-ish** (for `git show <tree-ish>:<path>`), each labeled. Area Explorers need the tree-ish,
   not the diff range, for Role 2 Step 1.
3. Symbols: for each file, the changed symbols with their line ranges. A symbol is a type,
   function, method, or configuration key. For a docs file, it is a heading.
4. Signatures: each changed public signature or exported name, old line and new line side by side.
5. Links: each changed file that calls, imports, or references a symbol that another changed file
   changes. Write "<file:line> uses <symbol> of <file:line>".
6. Tests: each changed test file, and the source files whose symbols it references.
7. Build and configuration: each changed manifest, configuration, migration, or build file.
8. Prior iterations: the commits of the range whose subject starts with "Review round", and the
   lines of the description of the target that mention a review. Copy them as they are. Do not
   judge whether they are resolved.
9. Not mapped: what you did not read or resolve, every cut that you made, and where you looked.
```

## Check the areas between Role 1 and Role 2

The orchestrator does this step itself, with no subagent. One area is one Area Explorer. The orchestrator can merge small areas or split large ones before Role 2. The "skipped" area gets no Area Explorer. The orchestrator reads its paths and the reason in brackets after each path. It moves any path that is not clearly a lock file or a generated file into another area. For each other area, it copies the file lines of the script and the map facts of these files into the Role 2 prompt.

## Role 2 — Area Explorers (parallel, one per area)

After the Target Explorer returns its map, with the files grouped by area, dispatch one subagent for each area, all in one message. They run in parallel, as `dev-essentials:subagent-orchestration` says. Each Area Explorer reads only the files of its own area, plus the sibling files that it needs for a comparison. It returns structured findings in the severity and type taxonomy of this skill, never on another scale. The section "Severity and type taxonomy" of `SKILL.md` has the tokens. The orchestrator never reads the files again itself.

Prompt template (fill one for each `<Area>`). Before the dispatch, replace `<FOCUS_LIST>` with the focus areas of the brief that matches the target type in `references/reviewer-briefs.md`. The subagent cannot read that file.

```text
You are reviewing the <Area> portion of <target identity> for the review-loop skill. The
orchestrating agent will receive your findings — it will NOT re-read these files itself.

Diff range: <the same diff range that the Target Explorer resolved, scoped to this area's files — for
`git diff`/`git log` only>
Source tree-ish: <the source tree-ish the Target Explorer resolved, per Role 1's tree-ish
resolution above — use this for `git show`, never the diff range>
Files in your area:
- <file1>  (production, +N lines)
- <file2>  (test, +M lines)
- …

Map facts for your area (from the Target Explorer, facts only):
<The Symbols, Signatures, Tests, and Build and configuration lines of the files above. Add every
Links line that touches one of these files, also a link from a file of another area.>

Prior iterations (for context only, do not raise these again unless the code regressed or the fix is incomplete):
<The Prior iterations lines of the map, unchanged.>

Step 1 — Start from the changed symbol ranges in the map facts. Read each file's contents from
the source tree-ish (not just the diff hunks — cross-file consequences are invisible in
isolation): `git show <tree-ish>:<path>` (or read the file directly for non-diff targets). Do not
pass the diff range here — `git show` needs a single tree-ish, not an `A...B` range.

Step 2 — For each new construct (class, wrapper, endpoint, converter, …), also read the most
similar existing sibling elsewhere in the repo to anchor your judgement of whether this follows
established convention or deviates from it.
To find candidates for that sibling, you can dispatch the agent type `dev-essentials:code-locator`
with the absolute worktree path and the question. It returns locations only. Choose the sibling
yourself.

Step 3 — Apply this focus-area list:
<FOCUS_LIST>
Also judge each non-trivial design decision in the changes against the established convention.

Step 4 — Use this skill's severity scale exactly: `Blocker`, `Critical`, `High`, `Medium`, `Low`,
`Nit` — do not invent your own scale. Use one type per finding from: `Bug`, `Reliability`, `Security`, `Performance`,
`Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`.

Report every finding that you find, at every severity, also one that you are not sure of. Phase 4
of the loop filters the findings, so a filter here drops real findings.

Return a structured list. Each finding has:
- severity: Blocker | Critical | High | Medium | Low | Nit
- type: Bug | Reliability | Security | Performance | Maintainability | Test | Style |
  Architecture | Spec | Docs
- file: full path
- line: anchor line number (or range "N-M")
- title: ≤80 chars one-liner
- diagnosis: ≤300 chars of why this matters
- fix direction: ≤200 chars — not the exact fix, just "refactor", "add validation", etc.
- confidence: high, medium, or low

Also return positive callouts (a `good`-flagged item, not a severity) — conventions this area
follows well. Be selective: one or two strong positives per file at most.

Do NOT include file contents or diff text in your response. The orchestrating agent will read
only the specific lines you anchor.

Keep each field to its limit above. Do not leave out a finding to make the response shorter.
```

## Step between Role 2 and Role 3 — collate

The orchestrator does this step itself, with no subagent. Merge the duplicates across areas (one issue that shows up in two areas) into one finding with several sites. Sort the findings by severity, then by file path.

## Role 3 — Main-agent synthesis (not a subagent)

The orchestrator reads only the lines that the findings point to. It reads them itself, with `Read` or with a targeted `git show <Source tree-ish>:<path> | sed -n`. The usual total is a few hundred lines for the whole target, at any target size.

For each finding, make sure that the diagnosis matches the lines. If the anchor is a few lines off, correct it. If the lines disprove the finding, drop it, and record it as REJECT-at-source in the list of rejected findings of Phase 9. If the findings become PR threads, make this check with care, because a posted comment cannot be edited through MCP. `help-review-pr` reads the lines again in its Phase 6 before the post.

With these lines, the orchestrator has all that it needs for the normal output of Phase 3. It writes the standard reviewer report in the **Full format** of `references/reviewer-briefs.md`, from the collated and checked findings. The report has the same summary table, the same severity and type columns, and the same footer "Review made by `<MODEL>`". The footer names the model that wrote the synthesis. The body of the report says that Area Explorer subagents found the findings, so that the record of Phase 9 stays honest about their source. Give that report to Phase 4 in the same way as the report of a single reviewer. Phase 4 and the later phases need no change for this mode. The Area Explorers return a fix direction, not a fix plan. So in `dev-essentials:review-loop`, the report has no Fix plan line, and step 5a plans the fixes with one plan dispatch.
