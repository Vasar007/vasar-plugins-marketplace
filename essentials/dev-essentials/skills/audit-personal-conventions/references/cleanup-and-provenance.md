# Cleanup and Provenance — Phase 9 Full Mechanics

Phase 9 of `SKILL.md` reads this file. It holds, in this order: the matrix of sub-phases, the 9a templates, the full 9c cross-repo mechanism (9c.0 to 9c.9), and the full 9d mechanism for personal entities.

---

## Default-on vs. opt-in matrix

| Sub-phase | Default | Opt-in flag | Touches |
| --- | --- | --- | --- |
| 9a, personal memory files | On (mode = `stub`) | `--cleanup-mode=annotate\|none` changes the mode. No flag turns off the index extension of 9a. | The non-repo configuration of the user under `<claude-root>` |
| 9b, global CLAUDE.md | Off (report-only) | `--update-global-claude-md` | The single global `<claude-root>/CLAUDE.md` |
| 9c, cross-repo project CLAUDE.md | Off (report-only) | `--cross-repo=all\|<repo>[,<repo>...]` | Tracked CLAUDE.md files in OTHER repos, through a branch and a PR |
| 9d, personal entities (commands, agents, skills) | Report-only | `--delete-personal-entities` | The personal global `commands/`, `agents/`, and `skills/` of the user under `<claude-root>` |

Phase 9 of `SKILL.md` gives the risk order of 9a to 9c. 9d sits between 9a and 9b. Like 9a, it touches only the non-repo configuration of the user. But a deletion is harder to undo than a stub of a memory file. So its opt-in path adds three gates before it removes anything (see 9d below).

With `--autonomous`, every gate and every question in this file passes without a stop. The precondition tests still run. See SKILL.md Phase 9.

---

## 9a — Standardized heading and bullet template

Extend the `MEMORY.md` index of the project under the `## Cross-project rules — migrated to marketplace skills` heading. Never invent another format from scratch.

Add one bullet for each promoted item. In this template and in every template below, `v<plugin-version>` is the recorded promotion version: the minimum plugin version that carries the rule. It is not the current version of the marketplace.

```markdown
- <rule summary> -> `<plugin>:<entity>` -> <date> -> v<plugin-version>
```

If the rule maps to only one part of a multi-rule entity, append `Rule N` or `§ section`:

```markdown
- <rule summary> -> `<plugin>:<entity>` (Rule 3) -> <date> -> v<plugin-version>
- <rule summary> -> `<plugin>:<entity>` (§ Cleanup and provenance) -> <date> -> v<plugin-version>
```

### Stub template (fully-promoted memory file, `--cleanup-mode=stub`, the default)

Replace the whole body with a one-line pointer. Keep the frontmatter of the file as it is:

```markdown
---
<original frontmatter, unchanged>
---

Migrated to `<plugin>:<entity>` on <date> (v<plugin-version>). See the marketplace entity for
current content; this file is intentionally left as a pointer only.
```

### Annotate template (fully-promoted memory file, `--cleanup-mode=annotate`)

Put a pointer above the body, and keep the body as it is:

```markdown
> Migrated to `<plugin>:<entity>` on <date> (v<plugin-version>). The content below is kept for
> historical reference; treat the marketplace entity as the current source of truth.

<original body, unchanged>
```

### Partial-promotion annotation (never stubbed)

If only a part of the content of a file was promoted, annotate only the promoted section, in place. Never replace the whole file, because the rest of the file is still live content:

```markdown
> The section below was promoted to `<plugin>:<entity>` on <date> (v<plugin-version>). Kept here
> for local context; the marketplace entity is authoritative for this rule specifically.

<original promoted section, unchanged>
```

### `--cleanup-mode=none`

Touch nothing at all for that item: no stub, no annotation, and no `MEMORY.md` index bullet for that promoted item. The other items of the same run that use `stub` or `annotate` still get their own index bullets. `none` applies to the one item that it was chosen for, not to the whole run. List the file as a manual TODO in the "Manual TODOs" list of the Phase 10 report. Add a one-line reminder of the mode that applies on a re-run.

---

## 9c — Cross-repo project CLAUDE.md files, full mechanism

This is the long form of the Phase 9c summary in `SKILL.md`. Read it before you run any part of 9c.

### 9c.0 — Classify the source file via git, not path shape

```bash
git -C <repo-root> ls-files --error-unmatch <path>   # tracked?
git -C <repo-root> check-ignore -v <path>             # ignored?
```

**Tracked** → the full cross-repo flow below. **Untracked or ignored** → treat it as a private local file. It takes the same path as 9b: a direct edit and a question for each file, with no branch and no PR.

### 9c.1 — Flag semantics

`--cross-repo=off|all|<repo>[,<repo>...]`, default `off`. Bare `--cross-repo` means `all`. The flag turns on a *capability*. It does not approve anything in advance. Each repo still needs its own push-gate `yes` at 9c.8, however the flag was set.

**9c-only re-entry mode**. With `--resume=<path>`, alone or with `--cross-repo=<value>`, the ignore-if-nothing-promoted rule below does not apply. Phase 9c then works on the promotion set that the `--resume` TODO file recorded in the earlier run (9c.7), although this run promoted nothing new. This mode makes the two-phase workflow possible: audit and promote now, then run 9c after the marketplace PR merges. Without the mode, the second run always promotes nothing, and the ignore rule always fires.

Outside the 9c-only re-entry mode, the run ignores `--cross-repo` with a warning in two cases only:

- This run promoted nothing, **AND** no `--resume` TODO file was given. Examples of a run that promotes nothing: a report-only run, a `--dry-run` run, or a run where the user declined the Phase 5 approval gate for everything.
- The flag names a repo that is not the source of any promoted rule of this run (or of the resumed TODO file).

### 9c.2 — Three preconditions (all required, checked per promotion)

| Precondition | Check | Failure behavior |
| --- | --- | --- |
| **A: the target marketplace side is published** | See "Precondition A" below. | Skip this repo. Defer it (9c.7). |
| **B: repo B can load the plugin** | Grep the tracked `.claude/settings.json` of repo B, or its own CLAUDE.md "Prerequisites" section, or both. Look for the target marketplace name and the owning plugin, registered or enabled. | Skip this repo. Report that the plugin needs a separate prerequisite PR in that repo, out of scope for a docs-only cleanup. Defer it (9c.7). |
| **C: the pointer is not orphaned** | `Load-bearing terms` is a comma-separated list (9c.7). Match each term as a **fixed string**, never as a regex. Terms can hold `.`, `[`, `*`, or a leading `-`. Run one grep for each term, at the same ref that Precondition A resolved and fetched: `git -C <marketplace-root> grep -n -F -e '<term>' origin/<default-branch> -- <entity-path>`. **Every** term must match. Quote one matching line for each term for the later push-gate display. | Skip this repo. Defer it (9c.7). |

#### Precondition A

1. Resolve the real default branch of the target marketplace with the fallback chain of 9c.4 step 1 below. Then run `git fetch origin <default-branch>` in the target marketplace repo. If the fetch fails (for example, no network or no configured remote), Precondition A fails. Do NOT fall back in silence to a stale local `<default-branch>` ref.
2. Run `git merge-base --is-ancestor <this-run-marketplace-head-sha> origin/<default-branch>`. This ancestor check tests whether the commit of this run is on the default branch.
3. Find out whether the files of the promoted entity exist at that ref: `git -C <marketplace-root> cat-file -e origin/<default-branch>:<entity-path>`. If they do not exist, Precondition A fails.
4. The checks of steps 2 and 3 are enough proof that the promotion is still published. They do not check content integrity, for example whether someone gutted or mangled the entity after the publish. Precondition C checks that.
5. **If the ancestor check of step 2 fails**, that alone is not a Precondition A failure. The object can also be missing locally, for example after a re-clone. That case is the same. A squash merge or a rebase merge discards the original commit on purpose, and the history of this marketplace uses such merges. Then the SHA is never an ancestor of `origin/<default-branch>`, although the promotion is published. In that case, use this fallback. If both of these hold, Precondition A passes:
   - The entity still exists at that ref (the `cat-file -e` check of step 3).
   - The published `plugin.json` version at that ref is `>=` the `@version` that the TODO entry holds. On a run without `--resume`, compare with the Phase 8 bump of this run.
6. The reference point is the version that this run promoted (the single bump of Phase 8). On a `--resume` run, the reference point is in the TODO file (9c.7). It is the per-edit `<plugin>:<entity>@<version>` block, which also holds the `Entity path` of that edit. It also includes the repo-level fields `Marketplace root`, `Marketplace remote`, and `Promoted commit`. Never use the live `plugin.json` version of today.
7. **On resume**, `<marketplace-root>` is the root that Phase 0 of `SKILL.md` already resolved for this run. It is the persisted `Marketplace root`, or an explicit `--marketplace=` with a matching remote, as the resume order of Phase 0 says. Read `<this-run-marketplace-head-sha>` directly from the persisted `Promoted commit` field. That field holds, wherever `<marketplace-root>` came from.
8. On resume, Precondition A also compares the remote of `<marketplace-root>` again with the persisted `Marketplace remote` field: `git -C <marketplace-root> config --get remote.origin.url`. A mismatch is a Precondition A failure, because `<marketplace-root>` then no longer points at the right repo. A mismatch has three possible causes:
   - The remote changed after Phase 0 resolved it.
   - The remote check of Phase 0 was inconclusive.
   - Phase 0 did no remote check (step 3, with no `--marketplace=` override).

The reason for B: the run can remove a rule from the CLAUDE.md of repo B although repo B cannot load the replacement. Then the other users of repo B lose the rule, and they have no way to load the plugin that now documents it.

If a precondition fails for a repo, skip that repo, record it in the deferred TODO (9c.7), and continue with the other repos.

### 9c.3 — Sequencing gate (asked once per run)

Before the run creates a worktree for ANY repo, show the results of the mechanical Precondition A checks. Then ask exactly once:

> Has the `<target-marketplace-name>` PR for this run been merged to its default branch, and are
> you ready for other repos to reference it? (yes / not yet)

Only an explicit `yes` lets the run go on. The run treats "sure", "ok", silence, and every other answer as "not yet". On any answer other than an explicit yes, stop: write the deferred TODO (9c.7), and touch nothing in any other repo.

The automated checks of Precondition A can already show a failure (not merged, or the entity is missing at the merged ref). In that case, skip the question. Report the failure, and defer directly.

### 9c.4 — Per-repo mechanism

Process the repos one after the other, in ascending order of absolute path. The order keeps the reports stable across runs. A STOP in one repo never aborts the other repos.

1. **Preflight**. Run a clean-tree check scoped to the target file. Also run a separate, looser check for unrelated dirt elsewhere in the repo (see the dirty-repo matrix below). Then find the real default branch:
   1. Run `git symbolic-ref refs/remotes/origin/HEAD`, and strip the prefix `refs/remotes/origin/` to get the bare branch name. This gives the real default of the remote, for example `main`, `master`, or `release/1.0/master`. Never assume `main` or `master`.
   2. If that command fails or prints nothing, run `git rev-parse --verify origin/main`, then `git rev-parse --verify origin/master`. Use the first one that succeeds.
   3. If none succeeds, **STOP and ask the user for the default branch**.

   Fetch the resolved branch. If the fetch fails (for example, no network or no configured remote), **STOP and ask the user**. Do NOT fall back in silence to a stale local `<default-branch>` ref.
2. **Branch name**. `<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>` (see `--branch-prefix` in the Arguments table of `SKILL.md`). Every repo of this run gets the same branch name. The prefix `chores/` fits better than `researches/`, because this is routine maintenance in the product repo of someone else, not exploratory work.
3. **Worktree creation**. If the target marketplace has its own worktree-management skill, delegate to it. In this marketplace, that skill is `dev-essentials:git-worktree-management`, with its pipeline mode. The `--cross-repo` flag and the 9c.3 sequencing gate already count as the approval, so the worktree skill needs no second question. If the target marketplace has no such skill, create the worktree directly with `git worktree add`, with the same path convention (`<repo-root>/.claude/worktrees/<branch>/`). Note the degraded path explicitly in the report.
4. **Surgical edit**. Remove the promoted section. Insert or extend the pointer with the 9c.5 template below. Touch nothing else. Before the commit, run `git status --porcelain`. It must show exactly the target file or files.
5. **Commit**. One commit for each repo. Stage with an explicit `git add <path>`, never with `-A` or `.`. The commit message names the target marketplace, the plugin, the skill, and the version. Take the marketplace name from the resolved `--marketplace` value. Never hardcode it:

   ```text
   Point CLAUDE.md at <plugin>:<entity> (v<plugin-version>) in <marketplace-name>

   Removed the local "<removed-section-heading>" section; replaced with a pointer bullet
   under "Cross-project rules — migrated to marketplace skills".
   ```

6. **Push gate**. See 9c.8.
7. **PR creation**, host-detected from `git config --get remote.origin.url`:
   - GitHub pattern + `gh` / GitHub MCP tooling available → use that, following
     `dev-essentials:github-mcp-conventions` (owner/repo passed verbatim on every call, per that
     skill's Rule 1 and Rule 2).
   - Any other host, or no matching tool: report the pushed branch and the composed PR title and body, ready to paste. Add a "create PR" URL pattern for the host, where you can derive one. Else, say "open a PR through your hosting provider".

### 9c.5 — Pointer template

Extend a `## Cross-project rules — migrated to marketplace skills` heading, and never add a second one. Reuse this exact heading text, by the convention of 9a, so that the tooling and habits of a repo around that heading keep working. Add one bullet for each promoted rule:

```markdown
- **<Rule title>** (<one-line gist, 5-15 words>) -> `<plugin>:<entity>`
```

Append `Rule N` or `§ section` as needed, by the same convention as 9a above. The one-line gist is required. It helps a reader of the CLAUDE.md of repo B whose plugin is not updated yet. That reader still gets the gist of the rule without the marketplace entity. Use an inline stub in place (keep the heading, and replace only its body with a short pointer blockquote) in one case only: other files of the repo refer to the removed heading text. Grep for that text first, before you assume that the extension of the index is safe.

### 9c.6 — Dirty-repo handling matrix

| Condition | Handling |
| --- | --- |
| Target file itself modified, staged, or in conflict | Hard STOP, no override |
| Rebase, merge, or cherry-pick in progress | Hard STOP, no override |
| Detached or unborn HEAD | Hard STOP, no override |
| Target file untracked | Send it to the other branch of 9c.0 (the private-file path), not to this flow |
| Worktree creation fails for any reason | Hard STOP, no override |
| Unrelated dirt elsewhere in the repo | Report it and ask once. Any answer other than an explicit yes means skip. The isolated worktree does not touch this dirt, but ask before you go on anyway |

Never force-push. Never amend or rebase the branch of repo B. Never stash a file of the user in repo B, and never discard it with `git checkout`. Never touch `.gitignore` or `.claude/settings.json` in repo B.

### 9c.7 — Deferred TODO artifact

Write one Markdown artifact in the CALLING repo, the repo where the user invoked this skill. Use the propose-then-ask pattern of Phase 10 for this artifact too. Propose a default path: next to the place where `--report=<path>` puts its report. If no such convention exists, use a sensible default like `.claude-audit-todo-<date>.md` in the current working directory. Ask before you write. If the user declines a file, print the full TODO content in chat instead, with the same content and format as the entry template below. `--resume=<path>` reads only a file. Print it with an explicit note: the user must save that block word for word to a file and pass its path as `--resume=<path>`. Until the user does that, this deferred promotion cannot resume.

**Write the TODO file each time that a repo is skipped or deferred, for any reason**. This includes the case where `--cross-repo` was `off` (the default) for a promoted rule from a tracked project CLAUDE.md file. It is not only for a set flag that failed a gate. The file makes the 9c-only re-entry mode (9c.1) usable in a later, separate run.

Write one entry for each pending repo. Inside it, write one `### <plugin>:<entity>@<version>` block for each pending edit. Repeat the block for every promoted section that lands in that repo, by the batching rule of 9c.9:

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

A later run resumes the file with `--resume=<path> --cross-repo=<repo|all>`, without a new full audit. The resume does **not** jump directly to 9c.4:

1. It re-enters at 9c.2 and checks the three preconditions again against the current state, because time went by since the earlier run. It uses the marketplace root that Phase 0 of `SKILL.md` already resolved for this run (see the resume order of Phase 0).
2. It runs the 9c.3 sequencing question again, once for the resumed set. The repeated gate keeps the guarantee of 9c.9 that sequencing is absolute.
3. Only then does it go on to 9c.4 for the named repo or repos.

The Phase 5 approval gate does NOT run again, because the TODO file of the original run already holds the approvals. On resume, the Precondition A checks `git merge-base --is-ancestor` and `git -C <marketplace-root> cat-file -e` (9c.2) use the `<marketplace-root>` that Phase 0 resolved. They read `<this-run-marketplace-head-sha>` directly from the persisted `Promoted commit` field. That field holds, wherever `<marketplace-root>` came from, and after any unrelated later version bump. The resumed run can start from a different location. Only the persisted `Promoted commit` is an immutable reference to what the original run promoted.

### 9c.8 — Verbatim push gate per repo

Before you ask, show these facts for each repo:

- The repo root and the remote.
- The branch and the worktree path.
- The commit SHA and the subject.
- The diff stat.
- The removed section heading or headings.
- The added pointer or pointers.
- The coverage quotes of Precondition C: one matching line for each term of `Load-bearing terms`. Run the per-term grep of Precondition C again on the current content of the published entity, and show its matching line for each term. Never show a stale quote from an earlier pass. This holds on every run. On a resume run, the grep takes the persisted `Load-bearing terms` from the TODO file. No Precondition C pass of the same run gives them.
- The result of Precondition B: "plugin enabled: yes".
- The source and target branches of the planned PR, and the status of any linked issue.

Then ask explicitly:

> Push this branch and open a PR? (yes / no / push-only)

- `no`: the branch stays local. The report lists it as prepared but not pushed.
- `push-only`: push without a PR.
- No separate question comes before the edit. The edit lands in an isolated worktree, which the working tree of the repo does not see until the push. So this push gate, which shows the diff, is the single decision point for the whole change of the repo.

### 9c.9 — Guardrails specific to 9c

- The `--cross-repo` flag does not approve anything in advance. Each repo still gets its own push-gate `yes`.
- Sequencing (the 9c.2 preconditions and the 9c.3 gate) is absolute. There is no exception for a change that is "only docs".
- One repo means one worktree, one branch, one commit, and one PR. Several promoted sections for the CLAUDE.md of one repo go into the single commit of that repo.
- Never force past a dirty product repo.
- No hard dependency on the tools of a specific host. Always keep a manual fallback: report the pushed branch and the composed PR text, and say "open a PR through your hosting provider".
- Worktrees stay until the PR merges, by the lifecycle rule of the worktree skill (see `dev-essentials:git-worktree-management` in the target marketplace, where it exists).
- Pointers always keep a one-line gist, so that they still help each reader whose plugins are not updated yet.

---

## 9d — Personal entities (commands/agents/skills) cleanup

9d applies to personal global commands, agents, and skills under `<claude-root>/{commands,agents,skills}` in two cases:

- An entity that this run promoted or E-fixed (Phase 6) fully supersedes the file.
- The classification step of Phase 3 classified the file **F-stale**, because an already-shipped marketplace entity supersedes its content. F-stale for an unrelated reason does not count, for example a dangling reference to a deleted file.

### Default — report-only

List each superseded personal file in the "Manual TODOs" list of the Phase 10 report, with a suggested manual action. The action is one of two: edit the file to point to the new marketplace entity instead of its own duplicated content, or delete the file outright. The list has the same shape as the entry for a project-repo CLAUDE.md file while `--cross-repo` is off:

```markdown
- `<claude-root>/commands/<name>.md` — superseded by `<plugin>:<entity>`. Suggested action: delete
  (its entire content is now covered by the promoted entity), or edit to reference it instead.
  Resume by re-running with `--scope=personal-entities --delete-personal-entities` — once the
  marketplace PR merges, if `<plugin>:<entity>` was promoted this run; immediately, if
  `<plugin>:<entity>` was already shipped.
```

This default deletes and edits nothing. The two routes recover in different ways:

- A deferral **promoted or E-fixed in this run** becomes reachable after the marketplace PR merges. A later run then classifies the file F-stale, because the entity is already shipped. The file then takes the F-stale branch of the same three gates below.
- An **already-shipped, F-stale** deferral needs no PR merge at all. No promotion of this run exists for a later re-entry to key on, but nothing waits on a merge either. Re-run the audit directly with `--scope=personal-entities --delete-personal-entities`.

### Partially superseded wrapper

A wrapper can still need its personal layer and also carry an F-stale section. The personal layer stays by the orthogonality rule of Step 4 in `references/classification-framework.md`, because it keeps B-taste or pure-forwarding sections. The F-stale section is a divergence that an upstream fix already removed. Step 4 tests the self-label of the wrapper against the current content of the shipped entity. Such a wrapper is **never eligible for deletion**, even with `--delete-personal-entities`.

Handle it like a partially promoted memory file in 9a, which the run never stubs. Report only. Name each section to trim, and the shipped entity and version that now covers it. The two recovery routes of 9d apply:

- A section that an EARLIER run fixed with E-fix-shipped can be trimmed now.
- A section whose fix landed in THIS run can be trimmed only after that promotion is published. The publish checks are the same as for a fully superseded file.

### Opt-in — `--delete-personal-entities` (bare boolean, default off)

This flag lets the skill delete the personal entity files in scope itself. Its gates are like the 9c sequencing gate. But personal entities belong to no target repo. So the gates cover only three checks: the marketplace-publish check, the content-integrity check, and a load check on the caller side. Precondition B has no *repo-side* counterpart here. Its frame of repo B protects the other users of a product repo, and that does not apply. But its concern does apply, aimed at the caller: do not remove an entry point whose replacement the user cannot load. The content-integrity check of Precondition C is on the marketplace side and applies unchanged. So step 1 below reuses both:

1. **Automated check of publication and local load**. Run it once for each run, before any question to the user. It runs Preconditions A and C of 9c.2 exactly as 9c.2 specifies them, against the target marketplace. This step does not restate their mechanics. Precondition A branches on the route that put the personal file in scope:

   - **Promoted or E-fixed in this run** (output of Phase 6): Precondition A **in full**. This includes its default-branch fallback chain and its fetch-failure rule. It also includes its fallback for a failed ancestor check: the entity still exists at the ref, AND the published `plugin.json` version at that ref is `>=` the promoted `@version`. The fallback matters most here. The history of this marketplace uses squash merges, so the raw `git merge-base --is-ancestor` check often fails on a published promotion. Without the fallback, this step falls back to report-only after every normal merge. The reference point is always the Phase 8 bump of this run and `<this-run-marketplace-head-sha>`, not a persisted TODO field. The re-entry mode of 9c.1 is for 9c only.
   - **Already shipped, F-stale** (classification of Phase 3): no commit of this run can prove the publication. The shipped entity that supersedes this file is older than this run. Precondition A still resolves the real default branch of the target marketplace with the fallback chain of 9c.4 step 1. It still runs `git fetch origin <default-branch>` under the same fetch-failure rule. A failed fetch is a hard Precondition A failure on this branch too, as on the promoted or E-fixed branch. This branch skips ONLY two checks: the ancestor check (`git merge-base --is-ancestor`) and the version-floor check of `plugin.json`. No commit of this run and no recorded promotion version exist for them to compare with. After the run resolves and fetches the default branch, the existence check is left: `git -C <marketplace-root> cat-file -e origin/<default-branch>:<entity-path>`.

   Precondition C is UNCHANGED on both branches. With the same mechanism, it checks again that the shipped entity still covers each term in the `Load-bearing terms` of the personal file. The "still published" proof of A explicitly does NOT cover mangled content, so cover every term. For each superseded personal file, run Precondition C at the same ref that A resolved and fetched:

   - Run one `git -C <marketplace-root> grep -n -F -e '<term>' origin/<default-branch> -- <entity-path>` for each comma-separated term.
   - Match each term as a fixed string, never as a regex.
   - Record one matching line for each term, for the per-file question of step 3.

   Then run the caller-side counterpart of Precondition B. It is the mechanism of B, with repo B replaced by the environment of the caller. Grep `<claude-root>/settings.json`, or the "Prerequisites" section of the global `<claude-root>/CLAUDE.md`, or both. Look for the target marketplace name and the owning plugin, registered or enabled. If the plugin is not registered, do not delete. Report that the user must turn on the plugin locally first. Then the user keeps a loadable replacement for the entry point that the run removes.

   If A, C, or the caller-side load check fails, go straight to the report-only default above. This holds for every personal entity file in scope of this run. Do not show the marketplace-publish gate or the per-file question below at all. 9c.3 skips its sequencing question in the same way after a failed automated check of Precondition A.

2. **Marketplace-publish gate**. Ask it once for each run, and only after step 1 passed. It reuses the style of the 9c.3 question ("is it merged, and are you ready"). The wording depends on the branch that step 1 took.

   For a file that this run promoted or E-fixed, ask this question, unchanged.

   > Has the `<target-marketplace-name>` PR for this run been merged to its default branch, and are
   > you ready to delete the personal file(s) it supersedes? (yes / not yet)

   For an already-shipped, F-stale file, the publication is already proven. The existence check of Precondition A and the coverage grep of Precondition C at the same ref prove it. So "has the PR for this run been merged" has no referent. Ask a readiness question instead. On this branch, `v<plugin-version>` is the published `plugin.json` version at `origin/<default-branch>`. It is for display only, because this branch has no promotion version of this run to use as a floor in a check. Ask this question.

   > `<plugin>:<entity>` (`v<plugin-version>`) is published on `<default-branch>` — ready to
   > delete the N personal file(s) it supersedes? (yes / not yet)

   Both branches still ask this gate. The proven publication makes the question shorter, but it does not remove it, because the deletion cannot be undone. Any answer other than an explicit `yes` falls back to the report-only default above for every personal entity file in scope of this run.

   Step 1 branches for each file on its route, but the run asks this gate once. A run can have both a deferral promoted or E-fixed in this run and an already-shipped, F-stale file in scope. Then ask the gate exactly once, with the stricter wording for the promoted or E-fixed file. That single `yes` covers every file in scope of the run, whatever route classified it. This follows the precedent of 9c.3: one absolute gate for the run, not a gate for each item.

3. **Per-file question**. Ask it after the automated checks of step 1 and the gate of step 2 passed. A deletion is harder to undo than a stub of a memory file. So treat it at least as carefully as the per-file question of 9b about a CLAUDE.md edit. Ask for each file, right before its deletion. Carry the matching Precondition C grep lines of step 1 as required coverage quotes: one matching line for each term, like the required coverage quotes of 9c.8. Ask this question.

   > Delete `<path>`? Its content is now covered by `<plugin>:<entity>` (`v<plugin-version>`), verified
   > at `origin/<default-branch>`: "`<matching line per term>`". (yes/no)

   `no`: leave the file in place. List it in the Phase 10 report as a manual TODO instead, with the same line shape as the report-only default above.
