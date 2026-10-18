# Full Audit Walkthrough — End-to-End Worked Example

A sanitized, fictional run from end to end. It covers the scan, the triage, a partial approval, authoring, review, one version bump, and all four Phase 9 cleanup sub-phases. Of these sub-phases, one is on by default, and one is skipped. One has a mixed outcome across two repos and resumes in a later invocation, and one is report-only. The rule content, the repo names (`RepoAlpha`, `RepoBeta`), and the branch prefix (`devuser`) are fictional. The name, the remote host, and the plugin root of the target marketplace appear only as placeholders (`<target-marketplace-name>`, `<git-host>`, `<plugin-root>`).

**Invocation:**

```text
audit-personal-conventions --scope=all --projects=auto --marketplace=. --target-plugin=dev-essentials --rounds=2 --interactive
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

39 files read across memory files and indexes, the global CLAUDE.md, 6 project CLAUDE.md files, and 4 personal global commands. 41 atomic rules extracted. One landmine from `references/source-inventory.md` came up in this pass: a dated append-block in one memory file. The 2026-03 entry superseded a 2025-11 entry on the same topic, so the run used the later entry.

---

## Phase 3 — Classify, cluster, corroborate

41 rules clustered into 13 candidates after corroboration.

---

## Phase 4 — Triage

```markdown
# Personal-convention audit — 2026-08-20

## 0. Disposition legend

(The six rows of the legend in the template, unchanged.)

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

Wrappers diffed: none (no personal command of this run is a wrapper).

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

Note: #2 was rejected, because the max-attempts default goes into the description of #1 and does not stand alone. #4 and #10 were deferred until the "needs your call" question of section 7 gets an answer. #13 was deferred explicitly. A dedicated `redact-auth-tokens` skill needs its own authoring pass, not a rushed fold-in next to the retry-backoff skill. Every other item that the reply does not name (#5, #6, #9, #12) is deferred by default. In practice, A and B items stay alone for good, because a later run shows them again only after new corroboration appears.

Item #2 was rejected out of the retry-policy cluster, so the shape of the new skill narrows to #1 + #3. This run has `--interactive`, so before authoring, the run showed the smaller shape and got a new yes: "a 2-rule skill covering backoff-with-jitter and retry logging".

---

## Phase 6 — Author approved entities

Pre-authoring HEAD captured before dispatching the authoring subagent:
`git -C <marketplace-root> rev-parse HEAD` -> `a1b2c3d`. Recorded as `<pre-authoring-sha>` for
Phase 7.

Two entities authored:

- **New skill** `dev-essentials:retry-backoff-policy`, with `## Rule 1 — Apply exponential backoff with jitter` and `## Rule 2 — Log every retry attempt`. Each rule has Why, How to apply, and Anti-patterns. Rule 1 cites `source: RepoAlpha/CLAUDE.md:22`, and Rule 2 cites `source: <claude-root>/projects/<project>/memory/http-clients.md:14`.
- **Edit** to `dev-essentials:example-markdown-fences`'s fence-style example.

Commit sequence:

```text
Add retry-backoff-policy skill
Fix example-markdown-fences fence-style example
```

The review-round commit (see Phase 7) follows once review completes.

---

## Phase 7 — Review loop

`dev-essentials:review-loop target=diff a1b2c3d..HEAD --rounds=2 --interactive`, run on the two authored or edited files. The range is a two-dot range from the `<pre-authoring-sha>` of Phase 6, not a branch-base `main...HEAD` diff. The call adds `--interactive`, because this run has it (Phase 7). The configured review-loop defaults of this session applied, because this session had them. Round 1: 1 Medium finding (a missing anti-pattern example in Rule 2). Fixed. Round 2: clean. Stop verdict: `stop-clean`.

Commit:

```text
Review round 1: Fix missing anti-pattern example in Rule 2
```

---

## Phase 8 — Finalize (version bump)

One bump: `dev-essentials` plugin `1.4.0` -> `1.5.0` (MINOR, a pure addition: one new skill, one additive fix to the example of an existing skill, and no invocation path removed or renamed).

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

`<claude-root>/projects/<project>/memory/markdown-fences-stopgap.md` (E-fix-shipped, #7, fully promoted, because the correction of the shipped skill now holds its content) -> stubbed:

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

Candidate #1 came in part from the global CLAUDE.md, so the line prints 1. It stays report-only, because this run did not pass `--update-global-claude-md`.

---

## Phase 9c — Deferred by default (no `--cross-repo` in the main run)

`--cross-repo` was not passed for the main audit run above, so 9c stays report-only for now. But the cluster of #1 and #3 comes in part from `RepoAlpha/CLAUDE.md`, and `RepoBeta/CLAUDE.md` also corroborates #3. Both are tracked project CLAUDE.md files. So the run still writes the 9c.7 deferred-TODO artifact, and a later run can resume it in the 9c-only re-entry mode. The run follows the propose-then-ask pattern of Phase 10:

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

`Marketplace root`, `Marketplace remote`, and `Promoted commit` are the immutable reference that this run resolved for its own Phase 8 bump. A resume always reads `Promoted commit` from here. `Marketplace root` is the default hint from which Phase 0 resolves on a later `--resume` invocation. Phase 0 uses it as it is, unless that invocation gives an explicit `--marketplace=` override with a matching remote (see SKILL.md Phase 0). Both fields stay, whatever version the `plugin.json` of `<target-marketplace-name>` reaches by then.

---

## Phase 9d — Personal entities (report-only, no promoted personal entities this run)

Neither of the two eligibility routes of 9d fired in this run. No promotion of this run superseded a personal command, agent, or skill file. Phase 3 also classified no file F-stale because of an already-shipped entity. So the report-only default of Phase 9d has nothing to list this time.

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

F1 [APPLY] — Rule 2 missing anti-pattern example; added "logging the full stack trace on every retry attempt, not just the final failure" as the anti-pattern.
source: <claude-root>/projects/<project>/memory/http-clients.md:14

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
<sha3> Review round 1: Fix missing anti-pattern example in Rule 2
a3f9c2e Bump dev-essentials plugin to 1.5.0   (local only — nothing pushed unless a Phase 9c push-gate said yes)
```

---

## Phase 9c — Cross-repo cleanup (resumed in a later, separate invocation)

Once the `<target-marketplace-name>` PR carrying v1.5.0 merged, the user re-invoked, in a separate
session, days later:

```text
audit-personal-conventions --resume=./.claude-audit-todo-20260820.md --cross-repo=RepoAlpha,RepoBeta
```

This run promotes nothing new. Without the resume, that fires the ignore-if-nothing-promoted rule and makes `--cross-repo` a silent no-op. Here the rule does not fire: `--resume=<path>` turns on the 9c-only re-entry mode. So Phase 9c works on the promotion set that the TODO artifact of the main run above recorded. It re-enters at 9c.2, then runs the 9c.3 sequencing question again, once for the resumed set, before it goes on to 9c.4. The Phase 5 approval gate does not run again. The TODO artifact already holds the resumed approvals (#1, #3).

**9c.2 preconditions checked again**. Phase 0 selects the persisted root (step 3). This invocation gave no `--marketplace=` override, and the persisted `Marketplace root` (`<repos-dir>/<target-marketplace-name>`) exists on disk (see SKILL.md Phase 0). Precondition A then compares that root with the persisted `Marketplace remote` (`https://<git-host>/<target-marketplace-name>`) through `git -C <repos-dir>/<target-marketplace-name> config --get remote.origin.url`. The remotes match, so the run trusts the root. Precondition A reads `Promoted commit` (`a3f9c2e`) directly from the `RepoAlpha` TODO entry above. This resumed run happens in a separate session, maybe from a different location, so only the persisted commit is a reliable reference. Then Precondition A runs `git merge-base --is-ancestor a3f9c2e origin/main` and `git -C <repos-dir>/<target-marketplace-name> cat-file -e origin/main:<plugin-root>/skills/retry-backoff-policy/SKILL.md` against that resolved root and the persisted commit. Precondition A now passes: the `<target-marketplace-name>` PR with v1.5.0 is merged to `main`, and the entity files exist at that ref. The result does not depend on the *current* version of the plugin. Otherwise, an unrelated later bump defers this resumed run forever. The user answers yes at the 9c.3 sequencing gate:

```text
Has the <target-marketplace-name> PR for this run been merged to its default branch, and are you
ready for other repos to reference it? (yes / not yet)
> yes
```

**RepoAlpha**: all three preconditions pass.

- A: passed, as shown above.
- B: `RepoAlpha/.claude/settings.json` lists `<target-marketplace-name>` and `dev-essentials` as enabled.
- C: the `SKILL.md` of the published skill contains the term "exponential backoff" of `Load-bearing terms`. The run quotes the matching line for the push gate.

Worktree created at `RepoAlpha/.claude/worktrees/devuser/chores/claude-md-promotion-20260820/`
(`devuser` is this run's `--branch-prefix`). Surgical edit removes the old retry-policy section from
`RepoAlpha/CLAUDE.md`, replaces it with:

```markdown
## Cross-project rules — migrated to marketplace skills

- **HTTP retry policy** (exponential backoff with jitter, max 5 attempts) -> `dev-essentials:retry-backoff-policy`
```

The run commits and shows the push gate with these facts: the repo and remote, the branch, the commit SHA, and the diff stat. It also shows the removed heading, the added pointer, the Precondition C quote, and the Precondition B result. Last, it shows the source and target branches of the planned PR. The user replies `yes`. The run pushes the branch and opens the PR through GitHub MCP, per `dev-essentials:github-mcp-conventions`. The remote of RepoAlpha matches the GitHub pattern, and GitHub MCP tooling is available in this session.

**RepoBeta**: fails Precondition B.

- A: passes (same marketplace PR).
- B: `RepoBeta/.claude/settings.json` does not list `<target-marketplace-name>` at all. The plugin is not registered in that repo.
- Skipped. Recorded in a new deferred TODO: the user must turn on `<target-marketplace-name>`/`dev-essentials` in RepoBeta in a separate prerequisite PR. That PR is out of scope for this docs-only cleanup.

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
