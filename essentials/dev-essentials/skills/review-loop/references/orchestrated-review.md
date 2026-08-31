# Orchestrated Review Mode — Context-Budget-Preserving Reviewer Dispatch

Referenced by Phase 3 of `SKILL.md`. This is an **alternative execution mode for Phase 3 only**,
for targets too large to comfortably fit in one reviewer's context — it does not replace the
default single/parallel reviewer dispatch, which stays the default for everything below the
threshold below. Read this file when Phase 3 decides to use orchestrated mode; otherwise use
`references/reviewer-briefs.md` as normal.

Mined from a validated end-to-end workflow (`help-review-pr` command's Orchestrator Workflow,
proven on four large PRs). The shape generalizes to any large `branch` / `pr` / `diff` / `commits`
target this skill supports.

---

## When to use this mode

Use orchestrated mode when the target is large enough that reading the full diff (or all changed
files) would crowd out the orchestrating agent's context for the rest of the loop (Phases 4–9),
or when `--reviewer-focus` narrowing alone doesn't bring the read volume down enough. Mirrors the
threshold used by the source command:

- **Diff/target size > ~2,000 lines, or > ~30 files changed** → orchestrated mode is a reasonable
  choice.
- **Below that threshold** → stay on the default Phase 3 flow (single reviewer or parallel
  reviewer pair/quad, briefed with the full diff per `references/reviewer-briefs.md`). Orchestrated
  mode adds dispatch overhead that isn't worth it for a small or medium target.

This is a judgment call, not a hard gate — a target just under the threshold with unusually wide
file spread (many small files across unrelated areas) may still benefit from orchestration; a
target just over it but concentrated in one file may not need it. State the choice made and why
in the cycle's brief output.

## What this mode dispatches (not how — see cross-reference below)

This file defines **roles and prompt shapes**: what each subagent is asked to do and what it must
return. It does not restate **dispatch mechanics** (how independent `Agent` calls are batched into
a single assistant message for concurrent execution, vs. genuinely sequential dispatch) — that is
`dev-essentials:subagent-orchestration`'s job. Follow that skill's rules for how these subagents
are actually launched; the roles below simply say which subagents to dispatch and in which
order/dependency chain.

Four roles, dispatched in this dependency order:

1. **Target Explorer** (always) — one subagent, produces a compact summary.
2. **Area Explorers** (always, once Target Explorer returns) — one subagent per logical area,
   dispatched together (independent — no cross-area dependency).
3. **Finding Verifier** (optional — see trigger below) — one subagent, re-checks every finding's
   anchor before it is trusted.
4. **Main agent synthesis** (not a subagent) — collates results into the same reviewer report
   format Phase 3 always produces, then hands off to Phase 4 unchanged.

The orchestrating agent (the one running Phase 3) never reads the full diff or full files itself —
only the Target Explorer's summary, the Area Explorers' structured findings, and, at the very end,
the specific lines those surviving findings anchor to.

---

## Role 1 — Target Explorer

One subagent, dispatched alone (its output gates Role 2's file assignment). Returns a compact
summary — **hard cap ≤400 words** — not raw diff or file contents.

Prompt template:

```text
You are exploring a large review target so the orchestrating review-loop agent can plan the
review without reading the diff itself.

Target: <branch diff origin/<base>...HEAD | PR <id> via GitHub MCP | commit range | file set>
<Include exactly what Phase 1 already resolved: branch/PR refs, or the file list, per the
target's resolution row in SKILL.md Phase 1. Do not ask the subagent to re-resolve the target.>

Also resolve, alongside the diff range above, a **source tree-ish** — a single ref usable with
`git show <tree-ish>:<path>` (a diff range like `A...B` is not valid there). Resolution by target:

- `target=branch` → `HEAD`.
- `target=pr <id>` → `origin/<sourceBranch>` (the same bare source branch name resolved for the
  diff in SKILL.md Phase 1).
- `target=commits <N>` → `HEAD`.
- `target=diff <range>` → the range's right-hand endpoint (`HEAD` when the range has no explicit
  right side).

Report it separately from the diff range — the two are never interchangeable.

Tasks:
1. <If target=pr: call `pull_request_read` per `dev-essentials:github-mcp-conventions` (explicit
   `owner` and `repo` on the call).>
2. Run: git diff --stat <range>; git log --oneline <range>.
3. Group the changed files into logical areas (by module/namespace/directory/feature — whatever
   grouping the codebase's own structure suggests). Do not force a fixed area list; let the
   codebase's actual boundaries define <Area1>, <Area2>, … .

Report back (≤400 words) and NOTHING else:
- Target identity (branch/PR/commit range), title/description one-liner if available.
- The resolved **diff range** (for `git diff`/`git log`) AND the resolved **source tree-ish**
  (for `git show <tree-ish>:<path>`) — report both explicitly and labeled, since Area Explorers
  need the tree-ish, not the diff range, for Role 2 Step 1.
- Total files / +lines / -lines / commits.
- A grouped file list: production vs. tests, sharded by area (<Area1>, <Area2>, …) with line
  counts per file.
- Any already-resolved review iterations or prior findings visible in the target's own history
  or description (so Area Explorers don't re-raise them).
- Anything that looks like a non-trivial design decision worth flagging to the Area Explorers.

Do NOT include raw diff content, file contents, or commit messages beyond one-liners.
```

## Role 2 — Area Explorers (parallel, one per area)

Once the Target Explorer returns its area-sharded file list, dispatch one subagent per area in a
single message — parallel, per `dev-essentials:subagent-orchestration`. Each Area Explorer reads
only its own area's files plus the comparison siblings it needs, and returns structured findings
in this skill's own severity/type taxonomy (see `SKILL.md` §"Severity and type taxonomy") — never
a different scale. The orchestrating agent never re-reads the files itself.

Prompt template (fill one per `<Area>`):

```text
You are reviewing the <Area> portion of <target identity> for the review-loop skill. The
orchestrating agent will receive your findings — it will NOT re-read these files itself.

Diff range: <the same diff range the Target Explorer resolved, scoped to this area's files — for
`git diff`/`git log` only>
Source tree-ish: <the source tree-ish the Target Explorer resolved, per Role 1's tree-ish
resolution above — use this for `git show`, never the diff range>
Files in your area:
- <file1>  (production, +N lines)
- <file2>  (test, +M lines)
- …

Step 1 — Read each file's contents from the source tree-ish (not just the diff hunks — cross-file
consequences are invisible in isolation): `git show <tree-ish>:<path>` (or read the file directly
for non-diff targets). Do not pass the diff range here — `git show` needs a single tree-ish, not
an `A...B` range.

Step 2 — For each new construct (class, wrapper, endpoint, converter, …), also read the most
similar existing sibling elsewhere in the repo to anchor your judgement of whether this follows
established convention or deviates from it.

Step 3 — Apply the focus-area list from `references/reviewer-briefs.md`'s Common Rules and the
brief matching this target's type (bugs/logic, security, data integrity, performance, DI
lifetime, contract breaks, test coverage — or the target-specific list, e.g. the `spec` brief's
ambiguity/undefined-behavior/contradiction list, if this is a non-code target).

Step 4 — Use this skill's severity scale exactly: `Blocker`, `Critical`, `High`, `Medium`, `Low`,
`Nit` (see `SKILL.md` §"Severity and type taxonomy" for definitions — do not invent your own
scale). Use one type per finding from: `Bug`, `Reliability`, `Security`, `Performance`,
`Maintainability`, `Test`, `Style`, `Architecture`, `Spec`, `Docs`.

Don't over-flag. Apply the density guardrail from SKILL.md's Guardrails section — only report
findings with real, actionable signal.

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

Done inline by the orchestrating agent, not a subagent. Collapse cross-area duplicates (the same
issue surfacing in two areas) into one multi-site finding. Rank by severity, then file path.

**Apply the density guardrail from `SKILL.md`'s Guardrails section here**: if the collated count
is wildly disproportionate to that baseline, challenge the Area Explorers' results — dispatch a
recheck of the offending area(s) with a stricter bar — before moving on to Role 3 or Phase 4's
triage table.

## Role 3 — Finding Verifier (optional)

Dispatch when accuracy is load-bearing and hard to walk back — e.g. `target=pr <id>` when the
findings will be posted as PR threads (`dev-essentials:github-mcp-conventions`: no comment-edit or
comment-delete via MCP once posted), or any run where the user has asked for a stricter pass. Skip
it for a routine local `branch`/`diff` review where findings only feed this skill's own Phase 4–5
loop and a wrong anchor just gets corrected in the next round.

One subagent, foreground, dispatched after collation. Re-reads each finding's anchor before
anything downstream trusts it.

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

Apply confirmed and refined findings; drop rejects (record them as REJECT-at-source in the
eventual Phase 9 rejected-findings list, same as any other rejected finding).

## Role 4 — Main-agent synthesis (not a subagent)

The orchestrating agent reads — inline, with `Read` or a targeted
`git show <Source tree-ish>:<path> | sed -n` — only the specific lines the surviving findings
anchor to. Typical total: a few hundred lines for the whole target, regardless of target size.

With that, the orchestrating agent has everything it needs to produce Phase 3's normal output:
compose the standard **Full format** reviewer report (`SKILL.md` §"Output formats → Full
format") from the collated, density-checked, (optionally) verified findings — same summary table,
same severity/type columns, same "Review made by `<MODEL>`" footer (name the synthesizing model;
note in the report body that findings were sourced from Area Explorer subagents so Phase 9's
provenance stays honest). Hand that report to Phase 4 exactly as if a single reviewer had
produced it — Phase 4 onward requires no changes for this mode.
