# Full Audit Walkthrough — End-to-End Worked Example

A sanitized, fictional end-to-end run covering scan, triage, partial approval, authoring, review,
one version bump, and all four Phase 9 cleanup sub-phases (one default-on, one skipped, one with a
mixed outcome across two repos resumed in a later invocation, one report-only). Rule content, repo
names (`RepoAlpha`, `RepoBeta`), and the branch prefix (`devuser`) are all fictional; the target
marketplace's name, remote host, and plugin root appear only as placeholders
(`<target-marketplace-name>`, `<git-host>`, `<plugin-root>`).

**Invocation:**

```text
audit-personal-conventions --scope=all --projects=auto --marketplace=. --target-plugin=dev-essentials --rounds=2
```

---

## Phase 0 — Resolve scope

```text
Scope resolved:
  --scope=all (memory, global-claude-md, project-claude-md, personal-entities)
  --projects=auto -> 9 projects resolved (2 worktree siblings collapsed into RepoAlpha)
  --marketplace=. -> "<target-marketplace-name>" @ <plugin-root> v1.4.0
  --target-plugin=dev-essentials
  --rounds=2, --cleanup-mode=stub, --update-global-claude-md (not set — default off), --cross-repo=off
  --branch-prefix=devuser (derived from RepoAlpha's own CLAUDE.md branch-naming convention)
```

---

## Phase 1-2 — Inventory and extraction

39 files read across memory files and indexes, the global CLAUDE.md, 6 project CLAUDE.md files, and 4
personal global commands. 41 atomic rules extracted. One landmine from `references/source-inventory.md`
triggered during this pass: a dated append-block in one memory file (the 2026-03 entry superseded a
2025-11 entry on the same topic — the later entry was used).

---

## Phase 3 — Classify, cluster, corroborate

41 rules clustered into 13 candidates after corroboration.

---

## Phase 4 — Triage

```markdown
# Personal-convention audit — 2026-08-20

## 1. Scan summary

| Source | Discovered | Read | Skipped (reason) |
| --- | --- | --- | --- |
| Memory files | 19 | 19 | 0 |
| MEMORY.md indexes | 9 | 9 | 0 |
| Global CLAUDE.md | 1 | 1 | 0 |
| Project CLAUDE.md | 9 | 6 | 1 (vendored, `--include-vendored` not set), 2 (worktree copy) |
| Personal commands | 4 | 4 | 0 |

Projects: 9 resolved (2 worktree siblings collapsed), 0 skipped.
Rules extracted: 41. Clusters after corroboration: 13.

## 2. Proposed changes, clustered by destination

### -> NEW skill `dev-essentials:retry-backoff-policy` (from #1, #2, #3)

- What it would contain: exponential-backoff retry policy for outbound HTTP clients, with jitter
  and a documented max-attempts default.
- Evidence: stated independently in the global CLAUDE.md, RepoAlpha's CLAUDE.md, and one memory
  file — 3 independent sources.
- Why an entity not memory: corroborated across 3 sources and cites an external authority (the
  shared `Acme.Http.Resilience` package's documented retry contract) — C-universal.
- Why this kind of entity: has phases (configure, apply, verify) and a worked example — skill, not
  command.

### -> EDIT shipped `dev-essentials:example-markdown-fences` (from #7)

- Current behaviour is wrong because: its table-formatting example uses a fence-style-mismatch that
  the linter now flags under a newer markdownlint version.
- Proposed change: correct the fence-style example; add one sentence noting the version dependency.

## 3. Every candidate — one row each

| # | Disposition | Rule (normalised) | Sources | Destination | Why this disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | C-universal | Retry with exponential backoff + jitter for outbound HTTP calls | 3 | new skill | Corroborated 3x; cites `Acme.Http.Resilience` contract |
| 2 | C-universal | Default max-attempts is 5 unless the call is idempotency-unsafe | 3 | new skill (same) | Same cluster as #1 |
| 3 | C-universal | Log every retry attempt at Warning, final failure at Error | 2 | new skill (same) | Corroborated 2x; cites team logging convention doc |
| 4 | D-scoped | RepoAlpha's queue consumer must ack only after retry policy exhausts | 1 | new skill, scoped section | Single-source but cites RepoAlpha's own queue contract doc |
| 5 | B-taste | Prefer `var` over explicit type in RepoAlpha's C# files | 1 | leave | No external authority beyond personal preference |
| 6 | A-local | RepoAlpha's staging DB connection string lives in `appsettings.Staging.json` | 1 | leave | Pure project-local trivia |
| 7 | E-fix-shipped | `dev-essentials:example-markdown-fences`'s fence example is stale for current markdownlint | 1 | edit shipped skill | Self-labelled "stopgap until example-markdown-fences is fixed" |
| 8 | F-stale | Memory file references a deleted `legacy-deploy.md` doc | 1 | prune | Target file verified deleted on disk |
| 9 | B-taste | 4-space indent preference in one memory file | 1 | leave | Preference only |
| 10 | D-scoped | RepoBeta's integration tests must reset the test container between suites | 2 | new skill, scoped section | Corroborated 2x; cites RepoBeta's test-harness README |
| 11 | F-stale | `MEMORY.md` index entry pointing at a file deleted 6 months ago | 1 | prune | Verified deleted |
| 12 | A-local | RepoBeta's dev-only feature-flag toggle procedure | 1 | leave | Pure project-local |
| 13 | C-universal | Never log a raw auth token, even at Debug level | 4 | new skill `dev-essentials:redact-auth-tokens` | Corroborated 4x; cites a documented secure-logging guideline |

## 4. Leave-alone detail (A and B)

| # | A/B | Rule | Why it stays put |
| --- | --- | --- | --- |
| 5 | B | `var` preference | No named team evidence, just personal style |
| 6 | A | Staging connection string location | Pure project trivia |
| 9 | B | 4-space indent | Preference only |
| 12 | A | Dev-only feature-flag toggle | Pure project trivia |

## 5. Fix-shipped-entity detail (E)

| # | Shipped entity | What's wrong | Source of correction | Proposed fix |
| --- | --- | --- | --- | --- |
| 7 | `dev-essentials:example-markdown-fences` | Fence-style example predates a markdownlint rule change | Memory file self-labelled "stopgap until example-markdown-fences is fixed" | Correct the example; note the version dependency |

## 6. Prunable (F)

| # | File | Why stale | Proposed action |
| --- | --- | --- | --- |
| 8 | `<claude-root>/projects/<project>/memory/deploy-notes.md` | References deleted `legacy-deploy.md` | Prune the dangling reference |
| 11 | `MEMORY.md` (RepoBeta) | Indexes a file deleted 6 months ago | Remove the stale index line |

## 7. Needs your call

- #4 and #10 are both D-scoped but target different repos' contracts — confirm whether they belong
  in the same new skill (two scoped sections) or two separate skills before authoring.

## 8. Approval

Reply with any combination:

    approve: 1,3,5-9,13
    defer:   4,10
    reject:  2
    approve all promotes
    approve none

Anything not named is treated as DEFERRED, never approved.
```

---

## Phase 5 — Approval gate

User replies:

```text
approve: 1,3,7,8,11
defer: 4,10,13
reject: 2
```

Note: #2 was rejected (the max-attempts default is folded into #1's own description instead of
standing alone), #4 and #10 were deferred pending the "needs your call" question in section 7, #13
was deferred explicitly (held back this run — a dedicated `redact-auth-tokens` skill needs its own
authoring pass, not a rushed fold-in alongside the retry-backoff skill), and
everything else not named (#5, #6, #9, #12) is deferred by default (in practice: permanently left
alone, since A/B items are re-surfaced each run only if new corroboration appears).

Because #2 was rejected out of the retry-policy cluster, the new skill's shape narrows to #1 + #3
— re-confirmed with the user as "a 2-rule skill covering backoff-with-jitter and retry logging"
before authoring proceeds.

---

## Phase 6 — Author approved entities

Pre-authoring HEAD captured before dispatching the authoring subagent:
`git -C <marketplace-root> rev-parse HEAD` -> `a1b2c3d`. Recorded as `<pre-authoring-sha>` for
Phase 7.

Two entities authored:

- **New skill** `dev-essentials:retry-backoff-policy` — `## Rule 1 — Apply exponential backoff
  with jitter` and `## Rule 2 — Log every retry attempt`, each with Why/How-to-apply/Anti-patterns,
  citing `source: RepoAlpha/CLAUDE.md:22` and `source: <claude-root>/projects/<project>/memory/http-clients.md:14`
  respectively.
- **Edit** to `dev-essentials:example-markdown-fences`'s fence-style example.

Commit sequence:

```text
Add retry-backoff-policy skill
Fix example-markdown-fences fence-style example
```

The "Apply review findings" commit (see Phase 7) follows once review completes.

---

## Phase 7 — Review loop

`dev-essentials:review-loop target=diff a1b2c3d..HEAD --rounds=2`, run against the two
authored/edited files — a two-dot range against Phase 6's `<pre-authoring-sha>`, not a branch-base
`main...HEAD` diff. This session's own configured defaults (Opus reviewer, Sonnet fixer) applied,
since they were present this session. Round 1: 1 Medium finding (a missing anti-pattern example in
Rule 2). Fixed. Round 2: clean. Stop verdict: `stop-clean`.

Commit:

```text
Apply review findings

F1 [APPLY] — Rule 2 missing anti-pattern example; added "logging the full stack trace on every
retry attempt, not just the final failure" as the anti-pattern.
source: <claude-root>/projects/<project>/memory/http-clients.md:14
```

---

## Phase 8 — Finalize (version bump)

One bump: `dev-essentials` plugin `1.4.0` -> `1.5.0` (MINOR — pure addition: one new skill, one
additive fix to an existing skill's example, no invocation path removed or renamed).

Post-bump tip captured, the same way Phase 6 captured `<pre-authoring-sha>`:
`git -C <marketplace-root> rev-parse HEAD` -> `a3f9c2e`. Recorded as
`<this-run-marketplace-head-sha>` for Phase 9c.

---

## Phase 9a — Personal memory cleanup (default-on)

`<claude-root>/projects/<project>/memory/http-clients.md` (fully promoted) -> stubbed:

```markdown
Migrated to `dev-essentials:retry-backoff-policy` on 2026-08-20 (v1.5.0). See the marketplace
entity for current content; this file is intentionally left as a pointer only.
```

`<claude-root>/projects/<project>/memory/markdown-fences-stopgap.md` (E-fix-shipped, #7, fully promoted —
its content is now folded into the shipped skill's correction) -> stubbed:

```markdown
Migrated to `dev-essentials:example-markdown-fences` on 2026-08-20 (v1.5.0). See the marketplace
entity for current content; this file is intentionally left as a pointer only.
```

`<claude-root>/projects/<project>/memory/deploy-notes.md` (F-stale, #8) -> the dangling
`legacy-deploy.md` reference is removed.

`RepoAlpha`'s `MEMORY.md` index extended:

```markdown
## Cross-project rules — migrated to marketplace skills

- Exponential backoff + jitter for outbound HTTP calls -> `dev-essentials:retry-backoff-policy` (Rule 1) -> 2026-08-20 -> v1.5.0
- Log every retry attempt at Warning, final failure at Error -> `dev-essentials:retry-backoff-policy` (Rule 2) -> 2026-08-20 -> v1.5.0
```

---

## Phase 9b — Global CLAUDE.md (skipped, not opted in)

`--update-global-claude-md` was not passed. Phase 9 report includes the exact line specified in
`SKILL.md`'s Phase 9b, with this run's actual count substituted:

```text
Global CLAUDE.md — 1 rule(s) could be replaced with a pointer; re-run with
`--update-global-claude-md` to apply
```

Candidate #1 was sourced in part from the global CLAUDE.md, so the line prints 1 — still
report-only, since `--update-global-claude-md` wasn't passed this run.

---

## Phase 9c — Deferred by default (no `--cross-repo` in the main run)

`--cross-repo` was not passed for the main audit run above, so 9c stays report-only for now — but
since #1/#3's cluster is sourced in part from `RepoAlpha/CLAUDE.md` and #3 is additionally
corroborated by `RepoBeta/CLAUDE.md`, both tracked project CLAUDE.md files, the 9c.7 deferred-TODO
artifact is still written so this can be resumed later, per the 9c-only re-entry mode. Following Phase 10's propose-then-confirm pattern:

```text
Write the Phase 9c deferred-TODO artifact to `./.claude-audit-todo-20260820.md`? (yes/no)
> yes
```

`./.claude-audit-todo-20260820.md` is written, listing `RepoAlpha` and `RepoBeta` as pending, each
blocked by "`--cross-repo` was off this run". The `RepoAlpha` entry, per the 9c.7 template:

```markdown
## RepoAlpha

- Absolute root: <repos-dir>/RepoAlpha
- Remote: https://<git-host>/RepoAlpha
- Base branch: main
- Planned branch: devuser/chores/claude-md-promotion-20260820
- Marketplace root: <repos-dir>/<target-marketplace-name>
- Marketplace remote: https://<git-host>/<target-marketplace-name>
- Promoted commit: a3f9c2e
- Blocked by: --cross-repo was off this run

### dev-essentials:retry-backoff-policy@1.5.0

- Target file: CLAUDE.md
- Entity path: <plugin-root>/skills/retry-backoff-policy/SKILL.md
- Load-bearing terms: exponential backoff
- Section to remove (verbatim): "## HTTP retry policy ..."
- Pointer bullet(s) to add: "- **HTTP retry policy** (exponential backoff with jitter, max 5
  attempts) -> `dev-essentials:retry-backoff-policy`"
```

`Marketplace root`, `Marketplace remote`, and `Promoted commit` are the immutable reference this run
resolved for its own Phase 8 bump. `Promoted commit` is always read from here on resume. `Marketplace
root` is the default hint Phase 0 resolves from on a later `--resume` invocation — used as-is unless
that invocation supplies an explicit, remote-verified `--marketplace=` override (see SKILL.md
Phase 0) — and both fields persist regardless of what `<target-marketplace-name>`'s `plugin.json`
version has climbed to by then.

---

## Phase 9d — Personal entities (report-only, no promoted personal entities this run)

Neither of 9d's two eligibility routes fired this run: no personal command/agent/skill file was
superseded by anything promoted in this run, and none was classified F-stale-because-already-shipped
by Phase 3 either. So Phase 9d's report-only default has nothing to list this time — the section
still prints "Personal entities — 0 file(s) superseded this run" per the skill's contract.

---

## Final report (Phase 10) for the main run

```markdown
# Personal-convention audit — run report

## Scope

all · 9 projects (2 worktree siblings collapsed) · target marketplace <target-marketplace-name> @ main

## Triage outcome

| Disposition | Candidates | Approved | Deferred | Rejected |
| --- | --- | --- | --- | --- |
| C-universal | 4 | 2 | 1 | 1 |
| D-scoped | 2 | 0 | 2 | 0 |
| E-fix-shipped | 1 | 1 | 0 | 0 |
| F-stale | 2 | 2 | 0 | 0 |
| A-local | 2 | 0 | 2 | 0 |
| B-taste | 2 | 0 | 2 | 0 |

## Shipped this run

| Entity | Kind | Plugin | Rules folded in (#) | Files |
| --- | --- | --- | --- | --- |
| `retry-backoff-policy` | new skill | dev-essentials | #1, #3 | SKILL.md |
| `example-markdown-fences` | edit | dev-essentials | #7 | SKILL.md |

## Review loop

2 rounds · 1 Medium (round 1, fixed) · APPLY=1 · stop-clean

## Version

dev-essentials 1.4.0 -> 1.5.0 (MINOR) — one bump, pure addition (one new skill, one additive fix)

## Source-side cleanup

| File | Action | Confirmed |
| --- | --- | --- |
| <claude-root>/projects/<project>/memory/http-clients.md | stub | yes |
| <claude-root>/projects/<project>/memory/markdown-fences-stopgap.md | stub | yes |
| <claude-root>/projects/<project>/memory/deploy-notes.md | prune dangling reference | yes |
| <claude-root>/projects/<project>/memory/MEMORY.md (RepoAlpha) | index extended | yes |
| <claude-root>/projects/<project>/memory/MEMORY.md (RepoBeta) | index entry #11 removed | yes |

Manual TODOs:

- RepoAlpha, RepoBeta: `--cross-repo` was off this run; deferred TODO written to
  `./.claude-audit-todo-20260820.md`. Resume later via
  `--resume=./.claude-audit-todo-20260820.md --cross-repo=RepoAlpha,RepoBeta`.

## Deferred and rejected (carried to next run)

| # | Disposition | Rule | Why not now |
| --- | --- | --- | --- |
| 2 | C-universal | Default max-attempts is 5 | Rejected — folded into #1's own description instead |
| 4 | D-scoped | RepoAlpha queue-consumer ack timing | Deferred pending destination confirmation |
| 10 | D-scoped | RepoBeta test-container reset | Deferred pending destination confirmation |
| 13 | C-universal | Never log a raw auth token, even at Debug level | Deferred — held back this run pending a dedicated authoring pass |

## Commits

<sha1> Add retry-backoff-policy skill
<sha2> Fix example-markdown-fences fence-style example
<sha3> Apply review findings
a3f9c2e Bump dev-essentials plugin to 1.5.0   (local only — nothing pushed unless a Phase 9c push-gate said yes)
```

---

## Phase 9c — Cross-repo cleanup (resumed in a later, separate invocation)

Once the `<target-marketplace-name>` PR carrying v1.5.0 merged, the user re-invoked, in a separate
session, days later:

```text
audit-personal-conventions --resume=./.claude-audit-todo-20260820.md --cross-repo=RepoAlpha,RepoBeta
```

This run promotes nothing new, which by itself would fire the ignore-if-nothing-promoted rule and
silently no-op `--cross-repo`. It doesn't here: `--resume=<path>` activates the 9c-only re-entry
mode, so Phase 9c operates on the promotion set recorded in the TODO artifact from the main run
above. It re-enters at 9c.2, then re-runs 9c.3's sequencing confirmation once for the resumed set,
before proceeding to 9c.4. Phase 5's approval gate is not re-run; the resumed approvals (#1, #3)
were already recorded in the TODO artifact.

**9c.2 preconditions re-checked** — Phase 0 selects the persisted root (step 3:
this invocation supplied no `--marketplace=` override, and the persisted `Marketplace
root` (`<repos-dir>/<target-marketplace-name>`) exists on disk — see SKILL.md Phase
0). Precondition A then validates that root against the persisted `Marketplace remote`
(`https://<git-host>/<target-marketplace-name>`) via `git -C <repos-dir>/<target-marketplace-name>
config --get remote.origin.url` — it matches, so the root is trusted — and reads
`Promoted commit` (`a3f9c2e`) directly from the `RepoAlpha` TODO entry above (this
resumed run happens in a separate session, possibly from a different location, so only
the persisted commit is a reliable reference), then runs `git merge-base --is-ancestor
a3f9c2e origin/main` and `git -C <repos-dir>/<target-marketplace-name> cat-file -e
origin/main:<plugin-root>/skills/retry-backoff-policy/SKILL.md` against that resolved
root and the persisted commit. Precondition A now passes (the `<target-marketplace-name>` PR
carrying v1.5.0 is merged to `main`; the entity files exist at that ref), independent of the
plugin's *current* version — an unrelated later bump would otherwise defer this resumed run
forever. User confirms the 9c.3 sequencing gate:

```text
Has the <target-marketplace-name> PR for this run been merged to its default branch, and are you
ready for other repos to reference it? (yes / not yet)
> yes
```

**RepoAlpha** — all three preconditions pass:

- A: confirmed above.
- B: `RepoAlpha/.claude/settings.json` lists `<target-marketplace-name>` and `dev-essentials` as
  enabled.
- C: the published skill's `SKILL.md` contains the load-bearing term "exponential backoff" —
  quoted for the push gate.

Worktree created at `RepoAlpha/.claude/worktrees/devuser/chores/claude-md-promotion-20260820/`
(`devuser` is this run's `--branch-prefix`). Surgical edit removes the old retry-policy section from
`RepoAlpha/CLAUDE.md`, replaces it with:

```markdown
## Cross-project rules — migrated to marketplace skills

- **HTTP retry policy** (exponential backoff with jitter, max 5 attempts) -> `dev-essentials:retry-backoff-policy`
```

Commit, push gate shown (repo/remote, branch, commit sha, diff stat, removed heading, pointer added,
Precondition-C quote, Precondition-B confirmation, planned PR source/target) — user replies `yes`.
Branch pushed; PR opened via GitHub MCP (RepoAlpha's remote matches the GitHub pattern and GitHub
MCP tooling is available in this session) per `dev-essentials:github-mcp-conventions`.

**RepoBeta** — fails Precondition B:

- A: passes (same marketplace PR).
- B: `RepoBeta/.claude/settings.json` does not list `<target-marketplace-name>` at all — the plugin
  is not registered in that repo.
- Skipped. Recorded in a new deferred TODO: enabling `<target-marketplace-name>`/`dev-essentials` in
  RepoBeta is a separate prerequisite PR, out of scope for this docs-only cleanup.

## Follow-up report (Phase 10) for the resumed run

```markdown
## Source-side cleanup

| File | Action | Confirmed |
| --- | --- | --- |
| RepoAlpha/CLAUDE.md | pointer bullet added, PR opened | yes |

Manual TODOs:

- RepoBeta: enable `<target-marketplace-name>`/`dev-essentials` in `.claude/settings.json`, then
  resume via `--resume=<new-deferred-todo-path> --cross-repo=RepoBeta`.
```
