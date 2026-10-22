# Orchestrated Review Mode — Context-Budget-Preserving Reviewer Dispatch

Phase 3 of `SKILL.md` uses this file. It is a **different way to run Phase 3 only**, for targets that are too large for the context of one reviewer. It does not replace the default dispatch of one reviewer or of parallel reviewers. That dispatch stays the default for every target below the threshold. If Phase 3 chooses this mode, read this file. Else use `references/reviewer-briefs.md` as normal.

The shape works for any large `branch`, `pr`, `diff`, or `commits` target of this skill.

---

## When to use this mode

Use this mode for a target that is too large to read in full. Such a read of the diff or of all changed files fills the context that the orchestrator needs for Phases 4 to 9. The mode also fits a target where `--reviewer-focus` alone does not reduce the reading enough.

- **Diff or target size over about 2,000 lines, or over about 30 changed files**: this mode is a reasonable choice.
- **Below that threshold**: stay on the default Phase 3 flow. That flow is one reviewer, or a parallel pair or quad, with the full diff in the brief of `references/reviewer-briefs.md`. This mode adds dispatch overhead, and a small or medium target does not need it.

The threshold calls for judgment. It is not a fixed gate. A target just under it can still need this mode, for example a target spread over many small files in unrelated areas. A target just over it can still do without this mode, for example a target in one file. State the choice and the reason in the Brief format of the cycle.

## What this mode dispatches (not how — see cross-reference below)

This file defines **roles and prompt shapes**: what each subagent does and what it returns. It does not repeat the **dispatch mechanics**, which `dev-essentials:subagent-orchestration` covers. An example is several independent `Agent` calls in one message, against calls in sequence. Follow that skill to launch these subagents. The roles below say which subagents to dispatch, and in which order.

Four roles, in this order of dependency:

1. **Target Explorer** (always): one subagent. It builds a fact map of the target, with no judgment.
2. **Area Explorers** (always, after the Target Explorer returns): one subagent for each logical area, all dispatched together. They do not depend on each other.
3. **Finding Verifier** (optional, see the trigger below): one subagent. It re-reads the anchor of every finding before anyone trusts the finding.
4. **Main-agent synthesis** (not a subagent): the orchestrator collects the results into the reviewer report format that Phase 3 always produces. Then Phase 4 continues with no change.

Models: dispatch the Area Explorers and the Finding Verifier on `--reviewer-model`, because they judge code. A command with no `--reviewer-model` dispatches them on the model of the session. Dispatch the Target Explorer as `general-purpose` with `model: "haiku"` and `effort: "low"`, because it only maps facts. In `dev-essentials:review-loop`, also pass `--reviewer-effort` to the Area Explorers and the Finding Verifier.

The orchestrator never reads the full diff or full files itself. It reads only the fact map of the Target Explorer and the structured findings of the Area Explorers. At the very end, it reads the lines that the remaining findings point to.

---

## Role 1 — Target Explorer

One subagent, dispatched alone, because its output decides the file assignment of Role 2. It builds a map of the target, not a review. The map holds facts only, each with `path:line` evidence. It makes no judgment, so the Area Explorers and the orchestrator do all the judging. It does not return raw diff or file contents.

The map lists each changed file once, inside Areas. The sections other than Areas have a cap of 150 lines in total. Areas has no cap and is never cut, so no file drops out of the review. If the map is too long, the Target Explorer cuts in this order: Links first, then Symbols, then Signatures. It never cuts Ranges or Areas. It records every cut under "Not mapped".

Use the model and the effort of the Models paragraph above. It needs Bash for `git diff`, so it is not `dev-essentials:code-locator`, which has no Bash. This dispatch has no auto-compact window. This is an accepted trade-off, so the agent reads the diff in parts.

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
- Skip lock files and generated files. List them by name only under Build and configuration.

Tasks:
1. <If target=pr: call `pull_request_read` per `dev-essentials:github-mcp-conventions` (explicit
   `owner` and `repo` on the call).>
2. Run: git diff --stat <range>; git log --oneline <range>. Then run
   git diff -U0 <range> -- <path> for one area or one file at a time.
3. Use Grep to find the links between the changed files.

Report the map in these sections, in this order, and NOTHING else. Every section except Areas
has a cap of 150 lines in total. If you must cut, cut Links first, then Symbols, then
Signatures. Never cut Ranges or Areas. Record every cut under "Not mapped".
1. Target: identity (branch, PR, or commit range), a one-line title if available, and the
   totals: files, +lines, -lines, commits.
2. Ranges: the resolved **diff range** (for `git diff` and `git log`) AND the resolved **source
   tree-ish** (for `git show <tree-ish>:<path>`), each labeled. Area Explorers need the tree-ish,
   not the diff range, for Role 2 Step 1.
3. Areas: every changed file, each listed once: path, change kind (added, modified, deleted,
   renamed), +lines, -lines. Group the files by top-level folder. While a group has more than
   10 files or more than 800 changed lines, split it by the next folder level. A file in the
   root folder goes in a group named "root". Group by path only, never by importance. One group
   is one Area Explorer. Write each area as its name and its file lines, production files before
   test files. The number of files in Areas must equal the total of files in Target.
4. Symbols: for each file, the changed symbols with their line ranges. A symbol is a type,
   function, method, or configuration key. For a docs file, it is a heading.
5. Signatures: each changed public signature or exported name, old line and new line side by side.
6. Links: each changed file that calls, imports, or references a symbol that another changed file
   changes. Write "<file:line> uses <symbol> of <file:line>".
7. Tests: each changed test file, and the source files whose symbols it references.
8. Build and configuration: each changed manifest, configuration, migration, or build file, and
   the lock files and generated files that you skipped.
9. Prior iterations: the commits of the range whose subject starts with "Review round", and the
   lines of the description of the target that mention a review. Copy them as they are. Do not
   judge whether they are resolved.
10. Not mapped: what you did not read or resolve, every cut that you made, and where you looked.
```

## Check the map between Role 1 and Role 2

The orchestrator does this step itself, with no subagent. It makes sure that the number of files in Areas equals the total number of files in Target. If the numbers differ, it gets the missing paths with `git diff --name-only <range>`. Then it adds each missing file to an area, or it dispatches the Target Explorer again for those paths. It can also merge or split areas before Role 2. For each area, it copies the map facts of that area into the Role 2 prompt.

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

Step 1 — Start from the changed symbol ranges in the map facts. Read each file's contents from
the source tree-ish (not just the diff hunks — cross-file consequences are invisible in isolation): `git show <tree-ish>:<path>` (or read the file directly
for non-diff targets). Do not pass the diff range here — `git show` needs a single tree-ish, not
an `A...B` range.

Step 2 — For each new construct (class, wrapper, endpoint, converter, …), also read the most
similar existing sibling elsewhere in the repo to anchor your judgement of whether this follows
established convention or deviates from it.
To find candidates for that sibling, you can dispatch the agent type `dev-essentials:code-locator`
with the absolute worktree path and the question. It returns locations only. Choose the sibling
yourself.

Step 3 — Apply this focus-area list:
<FOCUS_LIST>
The Target Explorer only mapped facts and judged nothing. You do all the judging for your area. This
includes spotting a non-trivial design decision in the changes and checking it against the
established convention.

Step 4 — Use this skill's severity scale exactly: `Blocker`, `Critical`, `High`, `Medium`, `Low`,
`Nit` — do not invent your own scale. Use one type per finding from: `Bug`, `Reliability`, `Security`, `Performance`,
`Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`.

Don't over-flag. A healthy density is about 1 Critical/High + 4 Medium + 3 Low/Nit per ~1,000
lines — only report findings with real, actionable signal.

Return a structured list. Each finding has:
- severity: Blocker | Critical | High | Medium | Low | Nit
- type: Bug | Reliability | Security | Performance | Maintainability | Test | Style |
  Architecture | Spec | Docs
- file: full path
- line: anchor line number (or range "N-M")
- title: ≤80 chars one-liner
- diagnosis: ≤300 chars of why this matters
- fix direction: ≤200 chars — not the exact fix, just "refactor", "add validation", etc.

Also return positive callouts (a `good`-flagged item, not a severity) — conventions this area
follows well. Be selective: one or two strong positives per file at most.

Do NOT include file contents or diff text in your response. The orchestrating agent will read
only the specific lines you anchor.

Hard cap: ≤600 words total for the response.
```

## Step between Role 2 and Role 3 — collate and check density

The orchestrator does this step itself, with no subagent. Merge the duplicates across areas (one issue that shows up in two areas) into one finding with several sites. Sort the findings by severity, then by file path.

**Apply the density guardrail of the section "Guardrails" of `SKILL.md` here**. If the collated count is far from that baseline, challenge the results of the Area Explorers. Dispatch a second review of the areas with too many findings, with a stricter bar. Do this before Role 3 and before the triage table of Phase 4.

## Role 3 — Finding Verifier (optional)

If accuracy matters and a mistake is hard to undo, dispatch this role. An example is `target=pr <id>`, where the findings become PR threads (`dev-essentials:github-mcp-conventions`: no comment edit or comment delete through MCP after a post). Another example is any run where the user asked for a stricter pass. Skip this role for a routine local `branch` or `diff` review. There, the findings only feed Phases 4 and 5 of this skill, and the next round corrects a wrong anchor.

One subagent, dispatched after the collation step. It re-reads the anchor of each finding before any later step trusts the finding.

Prompt template:

```text
You are the last-mile verifier for a review-loop cycle on <target identity>. The orchestrating
agent will triage these findings next. Accuracy is load-bearing — verify before anything is
trusted.

For each finding below, do exactly two things:
1. Run: <git show <Source tree-ish>:<finding.file> | sed -n '<finding.line>,+5p'> (or read the file
   directly for non-diff targets).
2. Read the window and answer: does the diagnosis match the code? Is the severity appropriate per
   this skill's severity scale (Blocker/Critical/High/Medium/Low/Nit)?

Findings:
<structured list from the collation step>

Return for each finding:
- id: <index>
- verdict: confirm | refine | reject
- refined-line: <N> (only if refine and the anchor was off by ≤5 lines)
- refined-diagnosis: <text> (only if refine and the original diagnosis overstated or understated
  the issue)
- reject-reason: <text> (only if reject)

Hard cap: ≤300 words.
```

Keep the findings with the verdict `confirm` or `refine`. Drop the findings with the verdict `reject`. Record each one as REJECT-at-source in the list of rejected findings of Phase 9, like any other rejected finding.

## Role 4 — Main-agent synthesis (not a subagent)

The orchestrator reads only the lines that the remaining findings point to. It reads them itself, with `Read` or with a targeted `git show <Source tree-ish>:<path> | sed -n`. The usual total is a few hundred lines for the whole target, at any target size.

With these lines, the orchestrator has all that it needs for the normal output of Phase 3. It writes the standard reviewer report in the **Full format** of `references/reviewer-briefs.md`, from the collated, density-checked, and (optionally) verified findings. The report has the same summary table, the same severity and type columns, and the same footer "Review made by `<MODEL>`". The footer names the model that wrote the synthesis. The body of the report says that Area Explorer subagents found the findings, so that the record of Phase 9 stays honest about their source. Give that report to Phase 4 in the same way as the report of a single reviewer. Phase 4 and the later phases need no change for this mode.
