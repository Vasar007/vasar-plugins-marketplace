# Cleanup and Provenance — Phase 9 Full Mechanics

Referenced by Phase 9 of `SKILL.md`. Holds the standardized heading/bullet format, the stub/annotate
templates, the full Phase 9c cross-repo design, the Phase 9d personal-entities design, and the
default-on-vs-opt-in matrix summarizing all four sub-phases.

---

## Default-on vs. opt-in matrix

| Sub-phase | Default | Opt-in flag | Touches |
| --- | --- | --- | --- |
| 9a — personal memory files | On (mode = `stub`) | `--cleanup-mode=annotate\|none` changes the mode; there is no flag to disable 9a's index-extension | The user's own non-repo config under `<claude-root>` |
| 9b — global CLAUDE.md | Off (report-only) | `--update-global-claude-md` | The single global `<claude-root>/CLAUDE.md` |
| 9c — cross-repo project CLAUDE.md | Off (report-only) | `--cross-repo=all\|<repo>[,<repo>...]` | Tracked CLAUDE.md files in OTHER repos, via branch + PR |
| 9d — personal entities (commands/agents/skills) | Report-only | `--delete-personal-entities` | The user's own personal global `commands/`, `agents/`, `skills/` under `<claude-root>` |

The risk gradient: 9a touches only the user's own private config and defaults on;
9b touches a file that loads into every session and requires per-file confirmation even when
opted in; 9c touches someone else's product repo and requires three independently-checked
preconditions, a once-per-run sequencing gate, and a per-repo push gate, on top of the opt-in flag.
9d sits between 9a and 9b: like 9a it touches only the user's own non-repo config, but deletion is
less reversible than stubbing a memory file, so its opt-in path adds three gates before removing
anything (see 9d below).

---

## 9a — Standardized heading and bullet template

Extend — never invent from scratch — the `## Cross-project rules — migrated to marketplace skills`
heading in the project's own `MEMORY.md` index. This heading follows the convention an earlier
ad-hoc promotion in this marketplace's history introduced; this skill standardizes and continues it.

One bullet per promoted item (`v<plugin-version>` here and in every template below is the recorded
promotion version — the minimum plugin version that carries the rule — not the marketplace's current
version):

```markdown
- <rule summary> -> `<plugin>:<entity>` -> <date> -> v<plugin-version>
```

Append `Rule N` or `§ section` when the rule maps to only one part of a multi-rule entity:

```markdown
- <rule summary> -> `<plugin>:<entity>` (Rule 3) -> <date> -> v<plugin-version>
- <rule summary> -> `<plugin>:<entity>` (§ Cleanup and provenance) -> <date> -> v<plugin-version>
```

### Stub template (fully-promoted memory file, `--cleanup-mode=stub`, the default)

Replace the entire body with a one-line pointer, keeping the file's own frontmatter intact:

```markdown
---
<original frontmatter, unchanged>
---

Migrated to `<plugin>:<entity>` on <date> (v<plugin-version>). See the marketplace entity for
current content; this file is intentionally left as a pointer only.
```

### Annotate template (fully-promoted memory file, `--cleanup-mode=annotate`)

Prepend a pointer, keep the body as-is:

```markdown
> Migrated to `<plugin>:<entity>` on <date> (v<plugin-version>). The content below is kept for
> historical reference; treat the marketplace entity as the current source of truth.

<original body, unchanged>
```

### Partial-promotion annotation (never stubbed)

When only part of a file's content was promoted, annotate only the promoted section in place —
never replace the whole file, since the un-promoted remainder is still live content:

```markdown
> The section below was promoted to `<plugin>:<entity>` on <date> (v<plugin-version>). Kept here
> for local context; the marketplace entity is authoritative for this rule specifically.

<original promoted section, unchanged>
```

### `--cleanup-mode=none`

Touch nothing at all for that item — no file stub/annotate AND no `MEMORY.md` index bullet for that
specific promoted item. Other items in the same run that used `stub`/`annotate` still get their own
index bullets normally; `none` is scoped to the one item it was chosen for, not to the whole run.
List the file as a manual TODO in the Phase 10 report's "Manual TODOs" list, with a one-line reminder
of which mode would apply if re-run.

---

## 9c — Cross-repo project CLAUDE.md files, full mechanism

This is the long form of `SKILL.md`'s Phase 9c summary. Read this before running any part of 9c.

### 9c.0 — Classify the source file via git, not path shape

```bash
git -C <repo-root> ls-files --error-unmatch <path>   # tracked?
git -C <repo-root> check-ignore -v <path>             # ignored?
```

**Tracked** → the full cross-repo flow below. **Untracked or ignored** → treat as a private local
file: same direct-edit-plus-per-file-confirmation path as 9b, no branch, no PR.

### 9c.1 — Flag semantics

`--cross-repo=off|all|<repo>[,<repo>...]`, default `off`. Bare `--cross-repo` means `all`. The flag
opts into a *capability* — it is not a pre-authorization. Every repo still needs its own push-gate
`yes` at 9c.8, regardless of how the flag was set.

**9c-only re-entry mode.** When `--resume=<path>` is supplied — alone, or combined with
`--cross-repo=<value>` — the ignore-if-nothing-promoted rule below does not apply. Phase 9c instead
operates on the promotion set recorded in the `--resume` TODO file from the earlier run (9c.7), even
though this run itself promoted nothing new. This is what makes the documented two-phase workflow
(audit + promote now, come back and run 9c once the marketplace PR is merged) actually reachable —
without this mode, the second invocation would always promote nothing by construction and the
ignore-rule would always fire.

Outside 9c-only re-entry mode, `--cross-repo` is ignored with a warning **only when** this run
promoted nothing (report-only run, `--dry-run`, or the user declined the Phase 5 approval gate for
everything) **AND** no `--resume` TODO was supplied — or when it names a repo this run (or the
resumed TODO) did not source any promoted rule from.

### 9c.2 — Three preconditions (all required, checked per promotion)

| Precondition | Check | Failure behavior |
| --- | --- | --- |
| **A — target marketplace side is published** | Resolve the target marketplace's actual default branch per 9c.4 step 1's fallback chain below, then run `git fetch origin <default-branch>` in the target marketplace repo (if the fetch fails — network unavailable, remote not configured, etc. — that is itself a Precondition A failure: do NOT silently fall back to a stale local `<default-branch>` ref); confirm `git merge-base --is-ancestor <this-run-marketplace-head-sha> origin/<default-branch>`; confirm the promoted entity's files exist at that ref with `git -C <marketplace-root> cat-file -e origin/<default-branch>:<entity-path>`. These two checks are sufficient proof the promotion is still published; content-integrity (has the entity been silently gutted or mangled since publish) is Precondition C's job, not A's. **If the ancestor check fails** — including when the object no longer exists locally at all, e.g. after a re-clone — do NOT treat that alone as a Precondition A failure: a squash or rebase merge (this very marketplace repo's own history uses exactly that) legitimately discards the original commit, so the SHA is never an ancestor of `origin/<default-branch>` even though the promotion is genuinely published; fall back instead to confirming (a) the entity still exists at that ref (the same `cat-file -e` check above) AND (b) the published `plugin.json` version at that ref is `>=` the `@version` persisted in the TODO entry (or this run's own Phase 8 bump, on a non-`--resume` run) — that combination satisfies Precondition A. The reference point is the version this run promoted (Phase 8's single bump), or on a `--resume` run the per-edit `<plugin>:<entity>@<version>` block (which also carries that edit's `Entity path`) together with the repo-level `Marketplace root`, `Marketplace remote`, and `Promoted commit` fields recorded in the TODO artifact (9c.7) — never today's live `plugin.json` version. **On resume**, `<marketplace-root>` is whatever SKILL.md's Phase 0 already resolved for this run (the persisted `Marketplace root`, or a remote-verified explicit `--marketplace=` — see Phase 0's resume order), and `<this-run-marketplace-head-sha>` is read directly from the persisted `Promoted commit` field, which remains authoritative regardless of where `<marketplace-root>` resolved from. Precondition A re-validates `<marketplace-root>`'s remote against the persisted `Marketplace remote` field via `git -C <marketplace-root> config --get remote.origin.url` — a mismatch here means the remote diverged since Phase 0 resolved it, Phase 0's own check was inconclusive, or Phase 0 never checked at all (step 3, no `--marketplace=` override was given), and is itself a Precondition A failure, since it means `<marketplace-root>` no longer points at the right repo | Skip this repo; defer (9c.7) |
| **B — repo B can load the plugin** | Grep repo B's tracked `.claude/settings.json` (and/or its own CLAUDE.md "Prerequisites" section) for the target marketplace name plus the owning plugin registered/enabled | Skip this repo; report that enabling the plugin there is a separate prerequisite PR, out of scope for a docs-only cleanup; defer (9c.7) |
| **C — the pointer is not orphaned** | `Load-bearing terms` is a comma-separated list (9c.7); match each term as a **fixed string**, never a regex (terms can carry `.`, `[`, `*`, or a leading `-`) — one grep per term: `git -C <marketplace-root> grep -n -F -e '<term>' origin/<default-branch> -- <entity-path>` at the same ref Precondition A resolved and fetched. **Every** term must match; quote one matching line per term for the eventual push-gate display | Skip this repo; defer (9c.7) |

Rationale for B specifically: removing a rule from repo B's CLAUDE.md without confirming repo B can
load the replacement strands repo B's other users — they lose the rule and have no way to load the
plugin that now documents it.

Any failing precondition for a given repo → skip that repo, record it in the deferred TODO (9c.7),
continue processing the remaining repos.

### 9c.3 — Sequencing gate (asked once per run)

Before any worktree is created for ANY repo, show the mechanical Precondition-A check results, then
ask exactly once:

> Has the `<target-marketplace-name>` PR for this run been merged to its default branch, and are
> you ready for other repos to reference it? (yes / not yet)

Only an explicit `yes` proceeds — "sure", "ok", silence, or anything else is treated as "not yet".
On anything but explicit yes: stop, write the deferred TODO (9c.7), touch nothing in any other repo.

If Precondition A's automated checks already show a failure (not merged, entity missing at the
merged ref), skip the question entirely — report the failure and defer directly.

### 9c.4 — Per-repo mechanism

Process repos sequentially, in ascending absolute-path order (stable reports across runs; one repo
STOPping never aborts the rest):

1. **Preflight.** A clean-tree check scoped to the target file, plus a separate looser check for
   unrelated dirt elsewhere in the repo (see the dirty-repo matrix below). Detect the actual default
   branch: (1) run `git symbolic-ref refs/remotes/origin/HEAD` and strip the
   `refs/remotes/origin/` prefix to get the bare branch name — this returns the remote's actual
   default (e.g. `main`, `master`, or `release/1.0/master`) — never assume `main`/`master`; (2) if
   that command fails or returns nothing, check `git rev-parse --verify origin/main` then
   `git rev-parse --verify origin/master` and use the first that succeeds; (3) if none succeeds,
   **STOP and ask the user for the default branch**. Fetch the resolved branch. If the fetch fails
   (network unavailable, remote not configured, etc.), **STOP and ask the user** — do NOT silently
   fall back to a stale local `<default-branch>` ref.
2. **Branch name.** `<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>` (see `--branch-prefix` in
   `SKILL.md`'s Arguments table), the same branch name across every repo touched in this run.
   `chores/` is chosen over `researches/` because this is routine maintenance in someone else's
   product repo, not exploratory work.
3. **Worktree creation.** Delegate to the target marketplace's own worktree-management skill if one
   exists (in this marketplace: `dev-essentials:git-worktree-management`), using its
   pipeline-mode / pre-confirmed path — the `--cross-repo` flag plus the 9c.3 sequencing gate already
   constitute confirmation, so there is no need for a second confirmation prompt from the
   worktree skill itself. If no such skill is available in the target marketplace, create the
   worktree directly with `git worktree add`, using the same path convention
   (`<repo-root>/.claude/worktrees/<branch>/`), and note the degraded path explicitly in the
   eventual report.
4. **Surgical edit.** Remove the promoted section; insert or extend the pointer per the 9c.5
   template below. Touch nothing else. Verify with `git status --porcelain` showing exactly the
   target file(s) before committing.
5. **Commit.** One commit per repo. Stage with an explicit `git add <path>` — never `-A` or `.`.
   Commit message names the target marketplace, plugin, skill, and version, with the marketplace
   name interpolated from the resolved `--marketplace` value, never hardcoded:

   ```text
   Point CLAUDE.md at <plugin>:<entity> (v<plugin-version>) in <marketplace-name>

   Removed the local "<removed-section-heading>" section; replaced with a pointer bullet
   under "Cross-project rules — migrated to marketplace skills".
   ```

6. **Push gate.** See 9c.8.
7. **PR creation**, host-detected from `git config --get remote.origin.url`:
   - GitHub pattern + `gh` / GitHub MCP tooling available → use that, following
     `dev-essentials:github-mcp-conventions` (owner/repo passed verbatim on every call, per that
     skill's Rule 1 and Rule 2).
   - Any other host, or the matching tool isn't available → report the pushed branch, the composed
     PR title/body ready to paste, and a host-appropriate "create PR" URL pattern if derivable, or
     "open a PR through your hosting provider" if not.

### 9c.5 — Pointer template

Extend — never duplicate — a `## Cross-project rules — migrated to marketplace skills` heading
(reuse this exact heading text, per 9a's own convention, so a repo's own tooling or habits around
that heading keep working) with one bullet per promoted rule:

```markdown
- **<Rule title>** (<one-line gist, 5-15 words>) -> `<plugin>:<entity>`
```

Append `Rule N` / `§ section` as needed, same convention as 9a above. The one-line gist is
load-bearing, not decoration — it is what lets anyone reading repo B's CLAUDE.md who has not yet
updated their plugin still get the gist of the rule without opening the marketplace entity. Only
fall back to an inline stub-in-place (keep the heading, replace only its body with a short pointer
blockquote) when the removed heading text is referenced elsewhere in the repo — grep for it first,
before assuming the extend-the-index approach is safe.

### 9c.6 — Dirty-repo handling matrix

| Condition | Handling |
| --- | --- |
| Target file itself modified/staged/conflicted | Hard STOP, no override |
| Rebase/merge/cherry-pick in progress | Hard STOP, no override |
| Detached or unborn HEAD | Hard STOP, no override |
| Target file untracked | Route to 9c.0's other branch (private-file path), not this flow |
| Worktree creation fails for any reason | Hard STOP, no override |
| Unrelated dirt elsewhere in the repo | Report and ask once; default answer on anything but explicit yes = skip. The isolated worktree does not touch this dirt regardless, but ask before proceeding anyway |

Never force-push. Never amend or rebase repo B's branch. Never stash or checkout-discard a user's
file in repo B. Never touch `.gitignore` or `.claude/settings.json` in repo B.

### 9c.7 — Deferred TODO artifact

Write one markdown artifact in the CALLING repo (wherever this skill was invoked from). Apply
Phase 10's own propose-then-confirm pattern to this artifact too: propose a default path — next to
wherever `--report=<path>` would otherwise go, or a sensible default like
`.claude-audit-todo-<date>.md` in the current working directory if no other convention exists — and
ask for confirmation before writing. If the user declines a file, print the full TODO content
inline in chat instead — identical content and format to the entry template below. Because
`--resume=<path>` reads a file and nothing else, say so explicitly when printing: the user must
save that block verbatim to a file themselves and pass that path as `--resume=<path>`; until they
do, this deferred promotion cannot be resumed.

**Written whenever any repo is skipped or deferred for any reason — including simply because
`--cross-repo` was `off` (the default) for a promoted rule sourced from a tracked project CLAUDE.md
file**, not only when `--cross-repo` was set but failed a gate. This is what makes the 9c-only
re-entry mode (9c.1) usable on a later, separate invocation.

One entry per pending repo, and within it one `### <plugin>:<entity>@<version>` block per pending
edit — repeat the block for every promoted section landing in that repo, per 9c.9's batching rule:

```markdown
## <repo-name>

- Absolute root: <path>
- Remote: <url>
- Base branch: <branch>
- Planned branch: <branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>
- Marketplace root: <path>
- Marketplace remote: <url>
- Promoted commit: <this-run-marketplace-head-sha>
- Blocked by: <reason — e.g. precondition B failure, "sequencing gate declined", "--cross-repo was off this run", or a 9c.6 dirty-repo skip/STOP, all repo-level reasons as-is; but when the reason is a precondition A or C failure — which are per-promotion, not repo-level — name the specific promotion inline, e.g. "precondition C failure for dev-essentials:foo@1.2.0">

### <plugin>:<entity>@<version>

- Target file: <path>
- Entity path: <path to the entity's files, relative to `Marketplace root`>
- Load-bearing terms: <term>[, <term>...]
- Section to remove (verbatim): <quoted section>
- Pointer bullet(s) to add: <quoted bullet(s)>
```

Resumable later via `--resume=<path> --cross-repo=<repo|all>` without re-running the whole audit.
Resume does **not** jump directly to 9c.4 — it re-enters at 9c.2 (re-checking the three preconditions
against current state, since time has passed, using whatever marketplace root SKILL.md's Phase 0
already resolved for this run — see Phase 0's resume order) and then re-runs 9c.3's sequencing
confirmation once for the resumed set, only then proceeding to 9c.4 for the named repo(s). Re-running
that gate rather than skipping it is what keeps 9c.9's "sequencing is absolute" guarantee intact.
Phase 5's approval gate is NOT re-run; the approvals being resumed were already recorded in the
original run's TODO artifact. On resume, Precondition A's `git merge-base --is-ancestor` and
`git -C <marketplace-root> cat-file -e` checks (9c.2) use that Phase-0-resolved `<marketplace-root>`
and read `<this-run-marketplace-head-sha>` directly from the persisted `Promoted commit` field, which
remains authoritative regardless of where `<marketplace-root>` resolved from or an unrelated later
version bump — the resumed run may be launched from a different location, and only the persisted
`Promoted commit` is an immutable reference to what the original run actually promoted.

### 9c.8 — Verbatim push gate per repo

Show, per repo, before asking:

- Repo root and remote.
- Branch, worktree path.
- Commit sha and subject.
- Diff stat.
- Removed section heading(s).
- Pointer(s) added.
- The Precondition-C coverage quotes — one matching line per load-bearing term, always the output of
  this run's own 9c.2 Precondition-C pass: re-run Precondition C's per-term grep against current
  content and display the resulting matching line for each term from the published entity, never a
  stale captured quote carried forward from an earlier pass. On resume specifically, this matters
  because the grep's input — the persisted `Load-bearing terms` — comes from the TODO artifact
  rather than from a Precondition-C pass run moments earlier in the same invocation, but the
  requirement to re-derive fresh applies on every run, not only a resumed one.
- The Precondition-B "plugin enabled: yes" confirmation.
- The planned PR's source/target branches and linked-issue status (if any).

Then ask explicitly:

> Push this branch and open a PR? (yes / no / push-only)

- `no` — stays local, reported as prepared-but-unpushed.
- `push-only` — push without opening a PR.
- There is no separate pre-edit confirmation step. The edit lands inside an isolated worktree,
  invisible to the repo's working tree until push — so this diff-bearing push gate is the single
  decision point for the whole repo's change.

### 9c.9 — Guardrails specific to 9c

- The `--cross-repo` flag is not a pre-authorization — every repo still gets its own push-gate
  `yes`.
- Sequencing (9c.2 preconditions + the 9c.3 gate) is absolute — there is no exception for "it's just
  docs".
- One repo = one worktree, one branch, one commit, one PR. Multiple promoted sections landing in the
  same repo's CLAUDE.md batch into that repo's single commit.
- Never force past a dirty product repo.
- No hard dependency on any specific host's tooling — always have a manual fallback (report pushed
  branch + composed PR text + "open a PR through your hosting provider").
- Worktrees persist until PR merge, per the worktree skill's own lifecycle rule (see
  `dev-essentials:git-worktree-management`, if present in the target marketplace).
- Pointers always keep a one-line gist so they degrade gracefully for anyone who has not yet updated
  their plugins.

---

## 9d — Personal entities (commands/agents/skills) cleanup

Applies to personal global commands, agents, and skills under
`<claude-root>/{commands,agents,skills}` that were fully superseded by an entity promoted or
E-fixed this run (Phase 6), **or** classified **F-stale** by Phase 3's classification step because
an already-shipped marketplace entity supersedes their content — not F-stale for an unrelated reason,
e.g. a dangling reference to a deleted file.

### Default — report-only

List each superseded personal file with a suggested manual action — either edit it to reference the
new marketplace entity in place of its own duplicated content, or delete it outright — in the
Phase 10 report's "Manual TODOs" list, the same shape already used for a project-repo CLAUDE.md file
when `--cross-repo` is off:

```markdown
- `<claude-root>/commands/<name>.md` — superseded by `<plugin>:<entity>`. Suggested action: delete
  (its entire content is now covered by the promoted entity), or edit to reference it instead.
  Resume by re-running with `--scope=personal-entities --delete-personal-entities` — once the
  marketplace PR merges, if `<plugin>:<entity>` was promoted this run; immediately, if
  `<plugin>:<entity>` was already shipped.
```

Nothing is deleted or edited under this default. The two routes recover differently, mirroring 9c.1's
"this is what makes re-entry reachable" framing:

- A **promoted/E-fixed-this-run** deferral becomes reachable once the marketplace PR merges — a
  later run then classifies the file F-stale-because-already-shipped, and it takes the F-stale
  branch of the same three gates described below.
- An **already-shipped/F-stale** deferral needs no PR merge at all: there is no this-run promotion to
  key a later re-entry off, but there is also nothing pending on one — just re-run the audit directly
  with `--scope=personal-entities --delete-personal-entities`.

### Opt-in — `--delete-personal-entities` (bare boolean, default off)

Allows the skill to delete promoted personal entity files itself, gated like 9c's sequencing gate
but scoped to the marketplace-publish and content-integrity checks plus a caller-side load check,
since personal entities are not tied to any target repo. There is no *repo-side* equivalent of
Precondition B — its repo-B framing, protecting a product repo's other users, doesn't apply — but its
underlying concern does, redirected at the caller: don't remove an entrypoint whose replacement the
user can't load. Precondition C's content-integrity check is marketplace-side and applies unchanged,
which is why step 1 below reuses both:

1. **Automated publish and local-load verification**, run once per run before showing any
   human-facing prompt — runs 9c.2's Preconditions A and C exactly as specified there, against the
   target marketplace, rather than restating their mechanics here. Precondition A's mechanics branch
   on which route classified the personal file in scope:

   - **Promoted/E-fixed this run** (Phase 6 output): Precondition A **in full**, including its
     default-branch fallback chain, its fetch-failure rule, and — load-bearing here — its
     ancestor-check-failure fallback (entity still exists at the ref AND the published `plugin.json`
     version at that ref is `>=` the promoted `@version`): this very marketplace's history is
     squash-merged, so the raw `git merge-base --is-ancestor` check routinely fails on a genuinely
     published promotion, and dropping the fallback would make this step report-only after every
     normal merge. The reference point is always this run's own Phase 8 bump and
     `<this-run-marketplace-head-sha>`, not a persisted TODO field — 9c.1's re-entry mode is 9c-only.
   - **Already-shipped/F-stale** (Phase 3 classification, new): there is no this-run commit to prove
     publication — the shipped entity superseding this file predates this run entirely. Precondition
     A still resolves the target marketplace's actual default branch via 9c.4 step 1's fallback chain
     and still runs `git fetch origin <default-branch>` under the same fetch-failure rule — a failed fetch is a hard
     Precondition-A failure on this branch too, exactly as it is on the promoted/E-fixed branch. ONLY
     the ancestor check (`git merge-base --is-ancestor`) and the `plugin.json` version-floor check are
     skipped on this branch: there is no this-run commit or recorded promotion version for either to
     compare against. What remains, once the default branch is resolved and fetched, is the existence
     check, `git -C <marketplace-root> cat-file -e origin/<default-branch>:<entity-path>`.

   Precondition C is UNCHANGED across both branches — same mechanism, re-verifying that the personal
   file's own load-bearing terms are still covered in the shipped entity. Per superseded personal
   file, Precondition C at the same ref A resolved and fetched — one `git -C <marketplace-root> grep
   -n -F -e '<term>' origin/<default-branch> -- <entity-path>` run per comma-separated term (each
   matched as a fixed string, never a regex) — against every one of that personal file's own
   load-bearing terms — since A's "still published" proof is explicitly scoped to NOT cover content
   mangling; record the matching lines — one matching line per load-bearing term — for step 3's
   per-file prompt below. Then the caller-side
   counterpart of Precondition B — B's mechanics with repo B replaced by the caller's own
   environment: grep `<claude-root>/settings.json` (and/or the global `<claude-root>/CLAUDE.md`
   "Prerequisites" section) for the target marketplace name plus the owning plugin registered or
   enabled. Not registered → do not delete; report enabling the plugin locally as a prerequisite, so
   the user isn't left without a loadable replacement for the entrypoint being removed. If A, C, or
   the caller-side load check fails, skip straight to the report-only default above for every personal
   entity file in scope this run — do not show the marketplace-publish gate or the per-file
   confirmation below at all — the same way 9c.3 skips its own sequencing question when Precondition
   A's automated checks already show a failure.

2. **Marketplace-publish gate**, asked once per run, only once step 1 has passed (reuses 9c.3's "has
   this been merged, are you ready" style confirmation). Wording depends on which branch step 1 took:

   - **Promoted/E-fixed this run** — unchanged:

     > Has the `<target-marketplace-name>` PR for this run been merged to its default branch, and are
     > you ready to delete the personal file(s) it supersedes? (yes / not yet)

   - **Already-shipped/F-stale** — publication is already mechanically proven by Precondition A's
     existence check plus Precondition C's coverage grep at the same ref, so "has the PR for this run
     been merged" has no referent; ask a readiness confirmation instead. On this branch,
     `v<plugin-version>` is the published `plugin.json` version read at `origin/<default-branch>` —
     display only, since this branch has no this-run promotion version to use as a floor/gate check:

     > `<plugin>:<entity>` (`v<plugin-version>`) is published on `<default-branch>` — ready to
     > delete the N personal file(s) it supersedes? (yes / not yet)

   Both branches still ask this gate — publication being already proven shortens the question, it
   does not remove it, since this is still an irreversible delete. Anything but an explicit `yes` —
   falls back to the report-only default above for every personal entity file in scope this run.

   Step 1 branches per file on which route classified it, but this gate is asked once per run. On a
   run whose scope contains both a promoted/E-fixed-this-run deferral and an already-shipped/F-stale
   file, ask the gate exactly once using the stricter promoted/E-fixed wording, and let that single
   `yes` cover every file in scope for the run regardless of which route classified it — mirroring
   9c.3's precedent of one absolute run-level sequencing gate rather than a per-item gate.

3. **Per-file confirmation**, once both step 1's automated checks and step 2's gate have passed.
   Deletion is less reversible than stubbing a memory file, so treat it at least as cautiously as 9b's
   per-file CLAUDE.md edit confirmation — ask individually, per file, immediately before each
   deletion, carrying step 1's matching Precondition-C grep lines as required coverage quotes — one
   matching line per load-bearing term, mirroring 9c.8's required coverage quotes:

   > Delete `<path>`? Its content is now covered by `<plugin>:<entity>` (`v<plugin-version>`), verified
   > at `origin/<default-branch>`: "`<matching line per term>`". (yes/no)

   `no` — leave the file in place; list it in the Phase 10 report as a manual TODO instead (same
   line shape as the report-only default above).
