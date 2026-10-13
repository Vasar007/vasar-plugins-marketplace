---
name: audit-personal-conventions
description: "Audit accumulated personal Claude Code convention — memory files, the global CLAUDE.md, each repo's own CLAUDE.md (including @-imports and scope overrides), and personal commands/agents/skills — and decide what deserves to become a reusable marketplace entity. Classifies each rule as project-local, personal taste, promotable (universal or scoped), a fix for an already-shipped skill, or stale, using cross-source corroboration and an on-disk-manifest already-promoted check. Presents the full triage, then by default approves the recommended items itself (with --interactive, waits for explicit approval) before authoring, review-looping, bumping the affected plugin version once, and (on request) updating CLAUDE.md files and memory indexes to point at the promotion. Triggers on requests like 'audit my memory', 'what in my memory should become a skill', 'promote my memory to skills', 'review my CLAUDE.md rules for promotion', 'which of my rules belong in the marketplace', 'clean up my project memory', or any session evaluating personal memory, CLAUDE.md, or personal commands for extraction into a shared plugin."
---

# Audit Personal Conventions

Accumulated personal convention — memory files, a global CLAUDE.md, per-repo CLAUDE.md files, and
personal global commands/agents/skills — grows without a review pass, mixing genuinely project-local
trivia, personal taste, rules corroborated across a dozen sources that clearly belong in a shared
plugin, and bug reports against already-shipped skills disguised as "stopgap" notes. Telling these
apart by eye, one file at a time, is how ad-hoc promotion runs turn into a pile of half-migrated
notes. This skill was designed by mining an earlier ad-hoc promotion of personal memory into a
marketplace, in this marketplace's own history, as a worked precedent, so it encodes that same
workflow instead of reinventing one from first principles.

**Hard requirement — no hardcoded marketplace name.** Every reference to "the marketplace" anywhere
in this skill's own body, phase prompts, output templates, and examples resolves from the
`--marketplace=` argument (default: the current working tree, if it contains
`.claude-plugin/marketplace.json`) and that marketplace's own `marketplace.json` `name` field. This
skill must generalize to promoting content into a *different* marketplace than the one it ships in
— do not name this marketplace, or any other specific marketplace, in prose, templates, or
examples — except to identify the provenance of an external, optional tool referenced in this
skill's own prose (not the promotion target, and not this skill's own shipping marketplace).

## When to use

- A deliberate audit pass across accumulated personal convention — "what in my memory should become
  a skill", "audit my CLAUDE.md rules", "clean up my project memory", a periodic sweep before a
  marketplace release.
- Deciding whether a rule that has come up more than once across sessions or repos deserves to
  become a shared entity, rather than living in one more memory file.

## When NOT to use

- Promoting a single, already-well-understood rule the user names directly ("turn this into a
  skill", pointing at one specific paragraph). That is a normal ad-hoc skill-authoring conversation
  — hand-author the entity directly, or use `skill-creator` if it is installed (an
  Anthropic-official plugin from the `claude-plugins-official` marketplace; it does not ship with
  this skill's own plugin). This skill exists for the audit-and-triage problem across many sources
  at once, not for a single deliberate extraction the user has already scoped themselves.

## Path resolution rule

Resolve the Claude config root from the `CLAUDE_CONFIG_DIR` environment variable if it is set, else
the user's home directory + `/.claude`. Never hardcode a username, drive letter, or absolute path
anywhere in this skill's text, prompts, or examples — always express paths relative to the resolved
config root or repo root.

## Arguments

| Flag | Default | Meaning |
| --- | --- | --- |
| `--scope=<tokens>` | `all` | Comma-combinable: `memory`, `global-claude-md`, `project-claude-md`, `claude-md` (alias for both claude-md tokens), `personal-entities` (personal global `commands/`, `agents/`, `skills/`), `all`. `all` combined with anything else → warn, treat as `all`. Unknown token → STOP, list valid tokens. |
| `--projects=auto\|none\|<list>` | `auto` | `auto` enumerates every directory under the resolved Claude projects dir (see Phase 0), decodes each encoded name by probing candidate filesystem paths, collapses worktree-suffixed siblings into their one real parent repo, reports the collapse count. `none` = global sources only. A list accepts project names, decoded paths, or encoded directory names; unresolvable entries STOP. |
| `--exclude-projects=<list>` | empty | Subtract from the `auto` set. |
| `--marketplace=<path>` | auto-detect | Target marketplace repo root — the repo receiving the promoted entities. Auto-detect = current working tree if it contains `.claude-plugin/marketplace.json`, else STOP and ask. This can be a DIFFERENT marketplace than the one this skill ships in. On `--resume=<path>`, resolution instead follows Phase 0's resume order (see Phase 0). |
| `--target-plugin=<name>` | none (ask if ambiguous) | Default destination plugin for promoted entities within the target marketplace; per-item overrides can be chosen during triage. |
| `--min-evidence=<N>` | `1` | Only present promotion candidates corroborated by at least N independent sources. |
| `--dispositions=<tokens>` | all | Filter the presented triage: `promote`, `promote-scoped`, `fix-shipped`, `prune`, `keep`. Maps onto the six-value disposition enum as: `promote`=C, `promote-scoped`=D, `fix-shipped`=E, `prune`=F, `keep`=A+B (both leave-alone dispositions collapse into one token since neither is ever actioned). `keep` items are always counted in the summary even if filtered out of the detail table. |
| `--include-vendored` | off (bare) | Include vendored/third-party CLAUDE.md files found inside personal repos (clearly labelled) instead of excluding them. |
| `--rounds=<N>` | `2` | Review cycles forwarded to the review-loop skill available in the target marketplace (see Phase 7). |
| `--cleanup-mode=stub\|annotate\|none` | `stub` | For FULLY-promoted memory files only. `none` = touch nothing at all for that item, not even its `MEMORY.md` index bullet. Full semantics in Phase 9a. |
| `--update-global-claude-md` | off (bare) | **Opt-in.** Without it, Phase 9b only REPORTS which global-CLAUDE.md rules could be replaced with a pointer and how to re-run to apply it — it edits nothing. With it, proceeds to per-file confirmation before writing (exact prompt in Phase 9b). |
| `--cross-repo=off\|all\|<repo>[,<repo>...]` | `off` | **Opt-in.** Enables Phase 9c (editing OTHER repos' tracked CLAUDE.md files). Bare `--cross-repo` = `--cross-repo=all`. Ignored with a warning only when this run promoted nothing AND no `--resume` TODO was supplied — see the 9c-only re-entry mode in Phase 9c and `references/cleanup-and-provenance.md`. |
| `--branch-prefix=<prefix>` | derive from context, else ask | Branch-name prefix for Phase 9c cross-repo branches (`<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>`). Default: derive it from the invoking session's own established branch-naming convention if stated anywhere accessible (a project's own CLAUDE.md, or the user's global CLAUDE.md); if none is found, ask the user once per run before creating the first cross-repo branch. |
| `--delete-personal-entities` | off (bare) | **Opt-in.** Allows Phase 9d to delete personal global command/agent/skill files superseded by an entity promoted this run, or by an already-shipped entity (then classified F-stale by Phase 3) — gated by the verification and confirmation steps in Phase 9d. Without it, Phase 9d only reports superseded files with a suggested manual action. |
| `--resume=<path>` | none | Resume a previously deferred Phase 9c cross-repo cleanup from its TODO file, without re-running the audit — enables the 9c-only re-entry mode (Phase 9c.1). Marketplace-root resolution on resume follows Phase 0's resume order. |
| `--dry-run` | off (bare) | Run Phases 0-4 only, stop after presenting the triage. No approval gate, no authoring, no cleanup. |
| `--report=chat\|<path>` | `chat` | Where the final report goes. |
| `--interactive` | off (bare) | Wait at the Phase 5 approval gate. Without it, Phase 5 approves the recommended items itself. See "Autonomy". |
| `--autonomous` | off | Do not stop at any gate, also before deletion, posts to outside systems, push, and pull request creation. Questions that block the work still stop. See "Autonomy". |

**Only `--autonomous` skips the Phase 9 gates, the per-repo push gate too.** The opt-in flags `--update-global-claude-md`, `--cross-repo`, and `--delete-personal-entities` turn on a capability. They do not skip its gates. The Phase 5 approval gate follows "Autonomy". By default, the run approves the recommended items itself. With `--interactive`, it waits.

## Autonomy

This workflow has three modes. The user picks one with a flag.

- Default (no flag): the run does not stop at its decision gates. A decision gate is a step where the workflow asks the user to approve a plan, a triage, a list, or an option. The dangerous gates still stop. A dangerous gate comes before deletion of data, a post to an outside system, a push, or pull request creation. Examples of posts: GitHub comments, reviews, and issues, or documentation pages.
- `--interactive`: every gate stops and waits for the user, as the gate text says.
- `--autonomous`: no gate stops, the dangerous gates too. The flag is the yes of the user at each gate of this workflow, also at a gate whose text asks for an explicit yes. Questions that block the work still stop (see below).

These rules apply in all modes:

- At a gate that does not stop, save what the gate shows in its usual file. If the gate has no file, put the content in the final report. Then take the default that the gate names, and continue.
- In the final report, list each gate that this run passed without a stop. With `--autonomous`, also list each deletion, post, push, and pull request that the run made.
- `--autonomous` removes stops. It does not add steps. Some steps run only with a flag such as `--push`, `--commit-push`, or `--apply`, or only on a request of the user. Such a step still needs that flag or request.
- A flag that names an action approves that action for this run, so the action needs no new stop. Examples: `--push` and `--commit-push`. An action that a step of this workflow names as its default needs no new stop either.
- If this workflow has a merge step and the branch policy allows a merge without a review, `--autonomous` merges. Else it does not merge. Never bypass branch protection. Do not use an admin override, a force push, or a change to the branch policy. In the other modes, the merge stays with the user.
- With `--autonomous`, do not destroy work that has no other copy. Examples: uncommitted changes, commits that no other branch or remote holds, and the only backup of changed files. Do not do such an action. List it in the final report.
- If the work cannot continue without an answer, ask the user. This applies in every mode. Examples: a required input is missing and has no safe default, or two readings of the task give different results. A failure that this run cannot fix also stops the run. Do not ask in other cases.
- A critical decision is a public contract change, a new dependency, a choice between designs, or a weaker test assertion. If the approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Without `--autonomous`, ask the user about every other critical decision.
- With `--autonomous`, make that decision yourself. Choose the option that follows the plan and the existing code. If neither one supports an option, choose the smallest change that keeps the current behavior. Never weaken a test assertion to make code pass. List each decision in the final report under "Decisions for your review".
- Without `--interactive`, do not ask before a Fable dispatch that neither the user nor the defaults of this workflow chose. Use Opus, and name the step in the final report.
- An instruction of the user in the conversation outranks these flags. For example, "pause before the push" stops the run before the push, also with `--autonomous`.
- If the run has both `--interactive` and `--autonomous`, stop before the first step, and ask the user once which mode to use.
- When this workflow runs another workflow and this run has `--interactive` or `--autonomous`, pass that flag on.

## Phases (the workflow)

### Phase 0 — Resolve scope

Parse flags. Resolve the Claude config root per the path resolution rule above. Resolve and validate
`--marketplace`:

**Non-resume runs** (no `--resume=<path>`): auto-detect against the current working tree's
`.claude-plugin/marketplace.json`, or use `--marketplace=` if supplied; STOP and ask if it cannot be
resolved either way.

**`--resume=<path>` runs** — after loading the TODO artifact, resolve the marketplace root in this
order:

0. TODO has no `Marketplace root` field (legacy artifact) — unchanged: `--marketplace=`/current
   working-tree auto-detect, STOP and ask if unresolvable.
1. `--marketplace=` is supplied AND `git -C <supplied> config --get remote.origin.url` matches the
   persisted `Marketplace remote` — use the supplied path (same repo, different clone location); echo
   the match.
2. Else `--marketplace=` is supplied and its remote definitely differs from a present persisted
   `Marketplace remote` — STOP and ask; never silently pick either (consistent with 9c.2 Precondition
   A already treating a mismatch as a hard failure).
3. Else the persisted `Marketplace root` exists on disk — use it (today's behavior; 9c.2
   Precondition A still re-validates its remote).
4. Else `--marketplace=` is supplied and the remote cross-check is inconclusive (no remote configured
   on the supplied clone, or the persisted `Marketplace remote` is absent) — use the supplied path
   with an explicit warning that the remote could not be cross-checked.
5. Else (persisted root missing on disk and no usable `--marketplace=`) — STOP and ask the user for
   the current clone path of the marketplace named in the TODO (display the persisted root and
   remote); validate the answer per step 1: a definite mismatch means re-ask, never accept; an
   inconclusive cross-check means accept with step 4's warning. Never fall through to CWD
   auto-detect on a resume run.

Build the project set per `--projects`, applying Phase 1's decode-and-probe and worktree-collapse
mechanics here, during scope resolution. Echo the fully-resolved scope (scope tokens, project count,
worktree-collapse count, any unresolvable encoded names, marketplace path and name, which source
won — persisted-unchanged / explicit-override-remote-matched / override-with-warning /
user-supplied-after-ask — target plugin if set) back to the user before reading anything.

### Phase 1 — Inventory (read-only)

For each in-scope source type, discover and read files using the discovery paths below, applying
the decode-and-probe procedure to resolve each project directory before reading its files. This
phase is read-only — no file is modified in Phase 1 under any flag combination.

#### Discovery paths per source type

| Source type | `--scope=` token | Discovery path(s) |
| --- | --- | --- |
| Per-project memory files | `memory` | `<claude-root>/projects/*/memory/*.md`, excluding `MEMORY.md` itself — the index belongs to the next row and is read once, as an index |
| Per-project memory index | `memory` | Usually INSIDE the `memory/` directory, at `<claude-root>/projects/<project>/memory/MEMORY.md`; a project may also have one at the outer level, `<claude-root>/projects/<project>/MEMORY.md` — probe both. This affects how the index's own bullets link to sibling files: an inner-location index links them bare (`feedback-x.md`), an outer-location index would need to prefix them with `memory/`. |
| Global CLAUDE.md | `global-claude-md` | `<claude-root>/CLAUDE.md` |
| Project CLAUDE.md | `project-claude-md` | `<repo-root>/CLAUDE.md`, `<repo-root>/.claude/CLAUDE.md`, and any other `CLAUDE.md` at nested depth — any `CLAUDE.md` under a subdirectory, other than the two paths already listed above and excluding any inside a `.claude/worktrees/` subtree, which is still enumerated for the skip count but never read (see worktree-copy exclusion below) — plus every file reachable via an `@`-import from any of those |
| Personal global commands | `personal-entities` | `<claude-root>/commands/*.md` |
| Personal global agents | `personal-entities` | `<claude-root>/agents/*.md` |
| Personal global skills | `personal-entities` | `<claude-root>/skills/*/SKILL.md` |

`claude-md` is an alias that expands to both `global-claude-md` and `project-claude-md`. `all`
expands to every token above.

**The discovery sets are disjoint — deduplicate before Phase 2.** Every row's *literal* path set
excludes what an earlier row already covers; the `@`-import expansion is the one set that can
legitimately reach a file another row also owns, so no file should be inventoried, read, cited, or
counted twice. After expanding all rows (root / `.claude` / nested / `@`-imports), deduplicate by
resolved absolute path, and count each surviving file exactly once in the Phase 4 scan summary and
*at most* once as an independent source in Phase 3 (independence is per distinct file, per
`references/classification-framework.md`'s definition; the worktree-sibling collapse below still
governs both which *repo* a rule is attributed to and how many independent sources one collapsed
worktree family contributes). A file reachable via `@`-import from two different
parents is one discovered file with one `source:` path — its inheritance scope is per landmine 8, but
its identity is the file.

#### Encoded project directory names — decode and probe

Claude Code stores each project's session/memory data under a directory whose name is an encoded
form of the project's filesystem path. The encoding is lossy and must be resolved by probing, not
by pure decoding:

1. **Single `-`** in the encoded name is ambiguous — it can represent a path separator (`/` or `\`)
   or a literal `.` in a real directory name. There is no unambiguous inverse transform.
2. **`--`** marks a separator immediately followed by a punctuation-prefixed segment — a
   drive-letter colon (e.g. `C--Users-...` decodes to a `C:\Users\...` root segment) or a
   dot-directory (e.g. a `.claude` subdirectory) inside an otherwise single-`-`-separated path.
   Treat this as what to try, not as ground truth.
3. Because of the single-`-` ambiguity, **decode by generating candidate paths and probing each
   candidate against the real filesystem** (does a directory exist at that candidate path?) rather
   than trusting a single deterministic decode. When more than one candidate resolves to an existing
   directory, prefer the candidate whose resolved path also contains a `.git` directory (i.e. is
   actually a repo root) — the strongest available signal, though not a hard requirement, since
   Claude Code keys a project directory off the working directory, not off repo root specifically.
4. If no candidate resolves, check for a worktree marker in the encoded name (see below) before
   excluding it — a project directory can encode a now-deleted git worktree whose accumulated
   memory would otherwise be lost. If a worktree marker is found, strip the worktree suffix and
   probe the parent path instead; if that resolves, attribute the directory's memory to the parent
   repo and count it toward the worktree-collapse total below, rather than dropping it silently.
   Only if the parent-path probe also fails, report the encoded name as unresolvable in the Phase 0
   scope echo and exclude it from the `auto` set.

#### Worktree-sibling collapse

A single repository worked on via multiple git worktrees produces multiple distinct encoded project
directories under `<claude-root>/projects/` — one per worktree path, all pointing at sessions and
memory for what is, from a promotion standpoint, the same one real repository.

- Detect a worktree-suffixed encoded name by the presence of a worktree marker in the decoded path
  (typically a `.claude/worktrees/<branch-ref>` segment, per
  `dev-essentials:git-worktree-management`'s path convention) — detection is
  convention-agnostic, so any worktree-path marker counts, not only that one.
- When one or more worktree-suffixed siblings decode to a path underneath a non-worktree sibling's
  resolved path, collapse them: treat the non-worktree sibling as the one real parent repo, and
  fold the worktree siblings' memory files into the same inventory pass (still individually cited
  by their own `source:` path in Phase 2 — collapsing decides which repo a rule belongs to for
  corroboration counting, it does not erase the distinct file paths). The same collapse applies to
  an all-worktree family too — a repo worked on exclusively via worktrees, with no non-worktree
  sibling anywhere in the resolved set (a realistic case, since always working through a worktree
  is itself an established convention). Detect this by reusing the decode-and-probe step 4
  mechanism above: strip each candidate's worktree-marker suffix and probe the stripped path; when
  two or more worktree-suffixed siblings' stripped paths resolve to the same underlying repo root,
  collapse them into one family even though none of them is a non-worktree sibling. Such a family
  has no parent project directory's copy to prefer as primary citation — see the parent-less case
  below.
- **A collapsed repo contributes one independent source per rule in Phase 3's corroboration count,
  not one per sibling.** The collapsed family — the parent project directory, if any, plus every
  worktree sibling folded into it — is one real repository, so an equivalent rule appearing in more
  than one of those directories' `memory/` files is the same repo's memory re-accumulated, not
  independent corroboration (the same distinction the `.claude/worktrees/` CLAUDE.md copies get
  below, applied to *counting* rather than to *reading*: those copies can be skipped outright,
  worktree memory cannot — per decode-and-probe step 4 it is content that exists nowhere else). This
  is a counting cap, not a content pick: the rule's content is still reconciled across every copy in
  the family, per landmine 5's "never arbitrarily pick one project's version and discard the other's
  additions" and calibration case 6's "reconcile drift, don't pick a copy" — no copy is ever dropped.
  Keep every file's own `source:` citation for provenance; when the family has a non-worktree
  parent, prefer the parent project directory's copy only as the cluster's primary citation for
  provenance/display purposes (mirroring the collapse rule above that treats the non-worktree
  sibling as the one real parent repo). When the family has no non-worktree parent (the all-worktree
  case above), there is no such
  preference — cite all copies as co-equal, and the family still counts as one source. The
  mechanism that identifies "the same rule" across worktree copies is Phase 3's own
  rule-equivalence clustering, already computed for every extracted rule; identical slug relative
  to each project's own `memory/` directory is simply the common, expected shape when a file was
  not renamed between worktrees, with landmine 5's reconcile rule still governing that file's
  content once matched. A rule that exists in a worktree sibling and nowhere else still counts as
  its own single source, and the cap applies only *within* one collapsed family — two different
  real repos stating the same rule are still two sources (calibration case 1).
- Report the collapse count in the Phase 0 scope echo: "`<w>` worktree siblings collapsed".
- The same duplication also happens *inside* a repo: a live worktree at
  `<repo-root>/.claude/worktrees/<branch-ref>/` is a full second checkout, so it carries its own
  copy of every one of that repo's `CLAUDE.md` files and their `@`-imports. Those copies are the
  same repo's rules re-read, not independent corroboration — enumerate any `.claude/worktrees/`
  subtree's `CLAUDE.md` files in the Discovered count same as any other file, but never read them;
  read each file only from the main checkout, and report the copies in the Phase 4 scan summary's
  Skipped column with the reason `worktree copy` — the same shape as the vendored skip (landmine 11
  in `references/source-inventory.md`), which is likewise discovered and counted but never read.

#### Wrapper personal entities — mandatory diff against the wrapped entity

For every personal-entities file that is a wrapper — whether by matching a landmine-12 signal
(introduced below, in **Structural landmines**; documented in full in
`references/source-inventory.md`), or by ordinary human judgment during the Phase 1 read — this
procedure is mandatory — never optional, and never skipped because the wrapper "looks like" it's
staying personal forever:

1. **Resolve the wrapped entity's on-disk path.** Reuse the EXISTING on-disk-manifest resolution
   mechanism from Phase 3 Step 2 (the same mechanism that greps actual plugin manifests in the
   target marketplace to check already-promoted status) — do not invent a second lookup path.
2. **Read the base entity's definition file(s), scoped to its kind** — the kind (skill vs. command
   vs. agent) is already known from step 1's on-disk-manifest resolution — recoverable from which of
   the `commands/`, `agents/`, or `skills/` trees the resolved entity file lives in; don't re-derive
   it:
   - **Skill** — read the base skill's `SKILL.md` in full, always — it is small and central, and it
     is never just the wrapper's own summary of what the base entity does. **Scope the read of its
     support files** (`references/`, `stages/`, `examples/`) the same token-budget-conscious way
     Precondition C (9c.2 C) checks whether a term still appears, instead of mandating a full read of
     every support file unconditionally:
     a. Extract the wrapper's own stated topics/terms — cheap, the wrapper file is small: its
        frontmatter `description`, headings, and any explicit "wraps/extends `<plugin>:<entity>`"
        language.
     b. Grep the base entity's support files for those terms
        (`git -C <marketplace-root> grep -n -F -e '<term>' -- <support-file-path>`, one search per
        term, the same fixed-string-not-regex discipline as Precondition C) to scope down which
        reference/stage/example files are actually relevant to this wrapper's claimed divergence.
     c. Fully read only the scoped-in files.
     Grep-first narrows the read; it does not replace judgment. An un-anticipated divergence — a
     support file the wrapper never mentions but silently duplicates or contradicts — can still
     require reading beyond the grep-matched set; if the scoped read leaves the wrapper's actual
     behavior unclear, widen it.
   - **Command or agent** — read the single `commands/<name>.md` or `agents/<name>.md` file in full,
     always. Commands and agents in the Claude Code plugin layout in general (not just this repo) are
     flat single files, not directories — there is no `references/`/`stages/`/`examples/` support-file
     tree to scope down; the full-file read already covers the entire base entity's own text, so step
     (a)-(c) above do not apply to this kind. But a command or agent routinely delegates behavior to
     another entity — identify this via a `Skill` tool invocation naming another skill, a `skills:`
     frontmatter entry, or an explicit `<plugin>:<entity>` reference (e.g. `commands/help-review-pr.md`
     sources its mechanics from `create-html-artifact`'s recipes and its tag taxonomy from
     `process-pr-comments`; `commands/research-implement-review-report.md` defers whole phases to
     `review-loop`) — and the wrapper's real divergence can lie in that delegated behavior, not
     just in the flat file's own text. Apply the same escape valve the skill branch above uses: if the
     wrapper's divergence bears on behavior it delegates to another entity, follow that ONE hop (don't
     chain further) and apply step (a)-(c) above's scoped-read approach to the delegated entity.
3. **Enumerate every divergence** between the wrapper and the base entity, and hand each one to
   Phase 2 as its own independent rule record — **except** a pure-forwarding/boilerplate divergence
   (argument passthrough, the wrapper's own flag parsing), which produces no Phase 2 record at all —
   it isn't a rule (the same exclusion that `references/classification-framework.md`'s "Wrapper
   divergences use the same rules, no new taxonomy" section already states). For every divergence
   that does become a record, the citation is a pair: the wrapper file:line, PLUS the base-entity
   file:line it diverges from.
4. **If the wrapped entity can't be resolved on disk** (renamed, removed, or the target marketplace
   doesn't ship it), record that as an unresolvable-source note in the Phase 4 scan summary — never
   silently skip the wrapper file.

#### Structural landmines

While reading, watch for the twelve structural landmines that cause silent misreads —
`references/source-inventory.md` documents all twelve with the correct handling for each; read it
before extracting rules, not after finding a diverged pair by accident.

### Phase 2 — Extract atomic rules

Produce one record per RULE, not per file — a single CLAUDE.md or memory file routinely mixes
categories, so classifying at file granularity misclassifies the mixed cases. Each record carries:

- A normalized one-line statement of the rule.
- A `source: <path>:<line>` citation — the same format Phase 6's own authored review-findings
  commits use for their numbered findings (`F1`/`F2`/`F3`, see
  `references/entity-authoring-conventions.md`), which is what lets an authoring commit later trace
  a generalized rule back to its origin.
- The source class (memory / global CLAUDE.md / project CLAUDE.md / personal entity).
- Any inheritance or scope qualifier discovered in Phase 1 (e.g. a nested CLAUDE.md that narrows or
  negates a parent rule).

### Phase 3 — Classify, cluster, corroborate

Full decision tree in `references/classification-framework.md`. Summary:

1. **Corroborate first.** Cross-source repetition of an equivalent rule is the strongest promote
   signal — count independent sources per cluster.
2. **Check already-promoted status against the target marketplace's actual on-disk plugin
   manifests.** Never trust a memory index's own "migrated" claim, and never trust the runtime
   skills listing (it mixes the user's personal global skills in with the target marketplace's
   actual shipped skills, and file location — not the listing — is what distinguishes them).
3. **Assign exactly one disposition** from the six-value enum:
   - **A-local** — leave. Genuinely project-local; no promotion value.
   - **B-taste** — leave, unless demonstrably an established team codestyle with named evidence.
   - **C-universal** — promote as a new entity, unscoped.
   - **D-scoped** — promote as a new entity, with the scope stated in the entity's own description.
   - **E-fix-shipped** — fix the existing shipped entity, then prune the source. Never a new entity
     for this disposition. Look for "stopgap until X is updated" phrasing — a near-certain marker.
   - **F-stale** — prune or annotate; no new content is produced.

**B-vs-C tie-breaker:** does the rule cite an external authority (an analyzer, a compiler error, a
shared package, a documented convention, an existing skill)? → C or D. Does it only assert a
preference with no external anchor? → B.

**`type:` frontmatter is never a category signal by itself** — content must be read regardless of
what a file's `type:` field claims. The field predicts nothing about disposition, in either
direction — see `references/classification-framework.md` calibration cases 3 and 4 for real examples
pointing opposite ways.

**Over-generalization screen:** before accepting a "universal" rule at face value, check whether its
only sanctioned exception is really one specific pipeline's internal stage numbering, or its entire
example list is really one pipeline's internal artifact names. When that is the case, generalize the
principle, keep the incident as a labelled worked example, and hedge the scope explicitly rather
than presenting a single incident as universal.

**Gap-vs-overlap check:** before proposing any new entity, check whether the capability is really a
gap between two existing entities, or an overlap with one that already covers it — extend the
existing entity instead of creating a near-duplicate.

### Phase 4 — Present the triage

Reproduce this template, adapting the bracketed placeholders and filling every table; do not change
the section structure. The "0. Disposition legend" table below is reproduced from Phase 3's own
six-value enum, so a reader of this output doesn't need to re-open
`references/classification-framework.md` to decode a disposition letter:

```markdown
# Personal-convention audit — <date>

## 0. Disposition legend

| Code | Name | Meaning |
|---|---|---|
| A | local | Genuinely project-local; no promotion value. Leave in place. |
| B | taste | Personal preference with no external authority behind it. Leave in place unless it's a demonstrably established team codestyle. |
| C | universal | Promote as a new entity, unscoped. |
| D | scoped | Promote as a new entity, with the scope stated in the entity's own description. |
| E | fix-shipped | Fix an existing shipped entity, then prune the source. Never a new entity. |
| F | stale | Prune or annotate the source; no new content produced. |

## 1. Scan summary

| Source | Discovered | Read | Skipped (reason) |
|---|---|---|---|
| ... | ... | ... | ... |

Projects: <p> resolved (<w> worktree siblings collapsed), <s> skipped.
Rules extracted: <r>. Clusters after corroboration: <c>.

Wrappers diffed: <wrapper file> → <base entity> (or "unresolvable on disk" per Phase 1's wrapper
procedure) — one row per landmine-12 wrapper found, so a missing diff is visible.

## 2. Proposed changes, clustered by destination

### → NEW skill `<plugin>:<name>` (from #.., #..)

- What it would contain
- Evidence
- Why an entity not memory
- Why this kind of entity

### → EDIT shipped `<plugin>:<entity>` (from #.., #..)

- Current behaviour is wrong because
- Proposed change

## 3. Every candidate — one row each

| # | Disposition | Rule (normalised) | Sources | Destination | Why this disposition |
|---|---|---|---|---|---|

## 4. Leave-alone detail (A and B)

| # | A/B | Rule | Why it stays put |
|---|---|---|---|

## 5. Fix-shipped-entity detail (E)

| # | Shipped entity | What's wrong | Source of correction | Proposed fix |
|---|---|---|---|---|

## 6. Prunable (F)

| # | File | Why stale | Proposed action |
|---|---|---|---|

## 7. Needs your call

- <ambiguities>

## 8. Approval

Reply with any combination:

    approve: 1,3,5-9,14
    defer:   4,11
    reject:  2
    approve all promotes
    approve none

Anything not named is treated as DEFERRED, never approved.
```

### Phase 5 — Approval gate (hard gate)

Without `--interactive`, the run answers this gate itself. It approves every C and D item that the triage recommends to promote, and every E item that it recommends to fix. It defers every F item and every item under "Needs your call". It writes these answers into the report in the "Approval" format, then starts Phase 6. With `--interactive`, wait for the reply of the user, as below.

Single global `#N` numbering across every table in Phase 4. Three verbs — `approve`, `defer`,
`reject` — plus two shorthands (`approve all promotes`, `approve none`). **Anything not named is
deferred, always** — there is no implicit approval.

`reject` vs `defer`: a rejected item is recorded rejected-with-reason and is not re-proposed
identically on the next run. A deferred item is expected to come back on a future run — it simply
wasn't decided this time.

If approving a subset of a cluster whose other members were deferred or rejected, re-scope the
destination entity to the approved subset and re-confirm the reduced shape before authoring (without `--interactive`, state the reduced shape in the report) — a
4-rule skill minus 3 deferred rules may no longer justify being its own entity.

**Approving an E item is its own risk class.** E means editing an already-shipped entity that other
sessions actively rely on. With `--interactive`, confirm each E item individually — never through `approve all promotes`,
which is scoped to new-entity promotions only.

### Phase 6 — Author approved entities

Before dispatching any authoring subagent, capture the pre-authoring HEAD SHA in the target
marketplace repo: `git -C <marketplace-root> rev-parse HEAD`. Record it as `<pre-authoring-sha>` —
Phase 7 needs it to scope the review loop to exactly this run's own authoring commits.

Full conventions in `references/entity-authoring-conventions.md`. Summary:

- **Skill vs. command vs. agent:** a command is a one-shot, single-file, user-typed procedure with
  no growth path. A skill is model-invoked, needs triggering plus progressive disclosure, and often
  needs multi-file depth. An agent is a persona pinned to a restricted tool allowlist. Pick based on
  which shape the approved rule(s) actually need, not habit.
- **This skill's own Phase 6 template sticks to `name` and `description`** by convention, not
  because the schema forbids more — `allowed-tools`, `model`, `context`, `disable-model-invocation`,
  `argument-hint`, and others are all valid optional skill frontmatter fields; add one only when the
  authored entity actually needs that specific behavior. `name` must equal the directory name
  exactly.
- **Description recipe:** what the entity covers and when to use it, an explicit enumeration of
  coverage, and a "Triggers on requests like..." clause.
- **Body structure:** H1 title, a provenance preamble, `## Rule N — <imperative>` sections each with
  Why / How to apply / Anti-patterns, and a closing cross-references section.
- **References vs. examples threshold is conditional need, not line count.** Split into a
  `references/` file only when a chunk of content applies to only one of several invocation
  branches, not because the file crossed some line count.
- **Commit discipline:** an "Add X" commit, followed later by an "Apply review findings" commit
  whose body cites numbered findings `F1`/`F2`/... each traced to a `source:` citation.

**No version bump happens in this phase.** Version bumps are Phase 8 only, after the shape has
settled.

### Phase 7 — Review loop

Invoke the review-loop skill available in the TARGET marketplace with `<marketplace-root>` as its
own working directory — `target=diff` resolves the range in the loop's own CWD, which would be the
wrong repo whenever the target marketplace differs from the one this skill was invoked from. If the
target marketplace is this one, that is
`dev-essentials:review-loop target=diff <pre-authoring-sha>..HEAD --rounds=<N>` (plus `--interactive` for a run that has it) — a two-dot
commit range against the SHA captured at the start of Phase 6, not a three-dot branch-base diff
(`<base>...HEAD`), which would also pull in commits the branch already carried from before Phase 6
and let the loop raise findings and apply edits against content that was never part of this run's
approved promotion. Use that skill's actual current flag syntax (`--flag=value` for value-taking
flags, with a required `target=` selector). If a different target marketplace ships an equivalent
review-loop skill, use that instead, adapted to its own actual interface. If neither is available,
degrade to a single-pass self-review and say so explicitly in the report — **this skill does not
hard-depend on `review-loop` existing in every possible target marketplace.**

Before invoking the loop, confirm the range still describes this run: if
`git -C <marketplace-root> merge-base --is-ancestor <pre-authoring-sha> HEAD` fails, STOP — the
range no longer describes this run's own commits (Phase 6 rebased, reset, or otherwise rewrote
history), and running the diff anyway would silently render unrelated pre-existing content as
deletions.

Apply this session's configured review-loop defaults if it has any (for example: 2 cycles, an Opus
reviewer, a Sonnet fixer, Opus also planning the fix) — but state them as "this session's configured
defaults, if any" rather than a hard requirement baked into this skill.

### Phase 8 — Finalize (version bump)

Exactly one version bump **per affected plugin**, in that plugin's own `plugin.json` only, done once
after Phase 7 has settled the final shape — not per-commit, and not speculatively before the shape
is final. A single run can legitimately touch more than one plugin (`--target-plugin` allows
per-item overrides); each affected plugin still gets exactly one bump for the run. Bump severity, at the highest severity that
plugin's own changes this run reached:

- **PATCH** — backward-compatible fixes only: typos, clarifications, wording tweaks, fixed examples.
  This is the bump an E-disposition-only run (fixing an existing shipped entity, no new entity)
  typically needs.
- **MINOR** — pure addition: new entities, additive changes to an existing entity.
- **MAJOR** — an existing invocation path was removed or renamed.

**Restart notice for brand-new entities.** If this run authored any brand-new skill, command, or
agent (a C-universal or D-scoped promotion — not an E-fix-shipped edit to something that already
existed), Phase 10's report must tell the user that a full Claude Code restart is required before the
new entity becomes invocable: `/plugin marketplace update` plus `/reload-plugins` refresh
hooks/MCP/LSP live, but do not rebuild the slash-command index for entities that did not exist
before this run. An E-only run (only an already-shipped, already-loaded entity was fixed in place)
does not need this — `/reload-plugins` alone picks up an edit to an entity the user's session has
already loaded — though restarting is always safe regardless of disposition.

Cautionary precedent: an earlier ad-hoc promotion in this marketplace's history made a mid-run extra
version bump that had to be reverted.

After the single version bump, capture the post-bump HEAD SHA in the target marketplace repo, the
same way Phase 6 captured `<pre-authoring-sha>`: `git -C <marketplace-root> rev-parse HEAD`. Record
it as `<this-run-marketplace-head-sha>` — it is the post-bump tip, not the pre-bump one, so
Precondition A's ancestor check (9c.2) covers every commit this run produced: the "Add X" commit(s),
any review-findings commit(s), and this version-bump commit.

### Phase 9 — Source-side cleanup

Four independently-gated sub-phases, each with its own risk profile — this is a risk gradient, not a
uniform report-only default. **9a (personal memory files) is on by default**, since it touches only
the user's own private, non-repo config; its behavior is governed by `--cleanup-mode` (`stub` by
default), not by an opt-in flag. **9b (global CLAUDE.md), 9c (cross-repo project CLAUDE.md), and 9d
(personal entities' opt-in deletion path) all require an explicit opt-in flag** — plus additional
confirmation before anything is written or deleted. **Nothing in any OTHER repository is ever touched
without `--cross-repo`.** See `references/cleanup-and-provenance.md`'s default-on-vs-opt-in matrix
for the full risk-gradient rationale.

With `--autonomous`, no gate of Phase 9 stops. This covers the 9a stub question, the 9b per-file question, and the 9c.3 sequencing gate. It also covers the 9c.8 push gate (push and open the PR) and the 9d confirmations. At the 9c.6 question about unrelated dirt, take its default: skip. At the 9c.7 path question, take the proposed path. The tests before each gate still run: Preconditions A, B, and C, and the hard stops of 9c.6. A failed test still skips or defers its repo or file. The final report lists each gate that passed and each push, PR, and deletion.

#### 9a — Personal memory files (default-on)

Governed by `--cleanup-mode`:

- A **fully-promoted** file → `stub` (replace the body with a one-line pointer), `annotate` (prepend
  a pointer, keep the body), or `none` (touch nothing at all for that item — no file stub/annotate
  AND no `MEMORY.md` index bullet for that specific item; skip, list as a manual TODO). Other items
  in the same run that used `stub`/`annotate` still get their own index bullets normally.
- A **partially-promoted** file → never stubbed. Annotate only the promoted section; the rest of the
  file stays as-is.

Without `--interactive`, no user reply at Phase 5 approved the cleanup, and `stub` deletes the body of personal memory files. So list the files that `stub` changes, and ask once before you write. With `--autonomous`, list them in the report, and write without the question. This question stays, although 9a is on by default, because no user reply approved the deletion. `annotate` and `none` need no question.

Extend — never invent from scratch — the project's own `MEMORY.md` index under a
`## Cross-project rules — migrated to marketplace skills` heading. One bullet per promoted item:
`rule summary -> <plugin>:<entity>` (append `Rule N` / `§ section` when the rule maps to one part of
a multi-rule entity) `-> date -> plugin version`.

Full templates and the standardized heading format live in `references/cleanup-and-provenance.md`.

#### 9b — Global CLAUDE.md (opt-in via `--update-global-claude-md`)

Without the flag: Phase 9's output includes a line — "Global CLAUDE.md — N rule(s) could be replaced
with a pointer; re-run with `--update-global-claude-md` to apply" — and nothing is written.

With the flag: for each promoted rule sourced from the global CLAUDE.md, show the exact diff
(removed prose → pointer) and ask, per file (there is only one global CLAUDE.md today, but the rule
is stated generally in case a future version of this skill treats other global files the same way):
"Replace this section of your global CLAUDE.md with a pointer to `<plugin>:<entity>`? (yes/no)".
Never batch-apply without per-file confirmation — this file loads into every session. With `--autonomous`, apply each replacement without the question, and list each one in the report.

#### 9c — Cross-repo project CLAUDE.md files (opt-in via `--cross-repo=`)

The structure below is complete, but the full gate text, the dirty-repo matrix, and the worked
mechanics live in `references/cleanup-and-provenance.md` — read it before running any part of 9c.

**9c.0 — Classify the source file via git, not path shape.** Run
`git -C <repo-root> ls-files --error-unmatch <path>` (tracked?) and
`git -C <repo-root> check-ignore -v <path>` (ignored?). Tracked → this cross-repo flow. Untracked or
ignored → treat as a private local file, using the same direct-edit-plus-per-file-confirmation path
as 9b, with no branch or PR involved.

**9c.1 — Flag.** `--cross-repo=off|all|<repo>[,<repo>...]`, default `off`; bare `--cross-repo` means
`all`. Opts into a capability, not a gate bypass — every repo still needs its own push-gate `yes` (or `--autonomous`)
(9c.8). **9c-only re-entry mode:** `--resume=<path>` (alone or combined with `--cross-repo=`) makes
Phase 9c operate on the promotion set recorded in the TODO file (9c.7) even though this run promoted
nothing new — the ignore-if-nothing-promoted rule below doesn't apply, and Phase 9c re-enters at 9c.2.
Outside that mode, `--cross-repo` is ignored with a warning only when this run promoted nothing AND no
`--resume` TODO was supplied, or if it names a repo nothing was sourced from — full conditions in
`references/cleanup-and-provenance.md` 9c.1.

**9c.2 — Three preconditions, ALL required, checked per promotion before anything is created:**

- **A — the target marketplace side is actually published.** Resolve the target marketplace's actual
  default branch the same way as 9c.4 step 1 below (fallback chain: `git symbolic-ref
  refs/remotes/origin/HEAD` → `git rev-parse --verify origin/main` → `git rev-parse --verify
  origin/master` → STOP and ask the user — never assume `main`/`master`), then run
  `git fetch origin <default-branch>` in the target marketplace repo. If the fetch fails (network
  unavailable, remote not configured, etc.), that is itself a Precondition A failure — skip this
  repo; defer (9c.7) — do NOT silently fall back to a stale local `<default-branch>` ref. Then
  confirm `git merge-base --is-ancestor <this-run-marketplace-head-sha> origin/<default-branch>`;
  confirm the promoted entity's files exist at that ref with
  `git -C <marketplace-root> cat-file -e origin/<default-branch>:<entity-path>`. These two checks —
  and the ancestor-check fallback below — are sufficient proof the promotion is still published;
  content-integrity (has the entity been silently gutted or mangled since publish) is Precondition
  C's job, not A's, in either case. **If the ancestor check fails** — including when the object no
  longer exists locally at all, e.g. after a re-clone — do NOT treat that alone as a Precondition A
  failure: a squash or rebase merge (this very marketplace repo's own history uses exactly that)
  legitimately discards the original commit, so the SHA is never an ancestor of
  `origin/<default-branch>` even though the promotion is genuinely published. Fall back instead to
  confirming (a) the entity still exists at that ref (the same `cat-file -e` check above) AND (b) the
  published `plugin.json` version at that ref is `>=` the `@version` persisted in the TODO entry (or
  this run's own Phase 8 bump, on a non-`--resume` run) — that combination satisfies Precondition A.
  The reference point is the version this run promoted (Phase 8's single bump), or on a `--resume`
  run the per-edit `<plugin>:<entity>@<version>` block (which also carries that edit's `Entity path`)
  together with the repo-level `Marketplace root`, `Marketplace remote`, and `Promoted commit` fields
  recorded in the TODO artifact (9c.7) — never today's live `plugin.json` version. On resume,
  `<marketplace-root>` is whatever Phase 0 already resolved for this run (the persisted `Marketplace
  root`, or a remote-verified explicit `--marketplace=` — see Phase 0's resume order), and
  `<this-run-marketplace-head-sha>` is read directly from the persisted `Promoted commit` field, which
  remains authoritative regardless of where `<marketplace-root>` resolved from. Precondition A
  re-validates `<marketplace-root>`'s remote against the persisted `Marketplace remote` field via
  `git -C <marketplace-root> config --get remote.origin.url` — a mismatch here means the remote
  diverged since Phase 0 resolved it, Phase 0's own check was inconclusive, or Phase 0 never checked
  at all (step 3, no `--marketplace=` override was given); that mismatch is itself a Precondition A
  failure (same routing as any other A failure), since it means `<marketplace-root>` no longer points
  at the right repo.
- **B — repo B can actually load the plugin.** Grep repo B's tracked `.claude/settings.json` (and/or
  its own CLAUDE.md "Prerequisites" section) for the target marketplace name plus the owning plugin
  being registered or enabled. If not registered, do NOT proceed for that repo — report that
  enabling the plugin there is a separate prerequisite PR, out of scope for a docs-only cleanup.
  Rationale: don't strand repo B's other users by removing a rule they have no way to load the
  replacement for.
- **C — the pointer is not orphaned.** Grep the published entity's files at
  `origin/<default-branch>` — the same ref Precondition A resolved and fetched, not the local
  working tree (C runs per-promotion after A, so it reuses A's already-resolved branch rather than
  re-resolving it) — for the rule's load-bearing terms. `Load-bearing terms` is a comma-separated
  **list** (9c.7's TODO schema), and each term is matched as a **fixed string, never as a regex** —
  code-like terms routinely carry `.`, `[`, `*`, or a leading `-`, which a bare pattern would either
  over-match or mis-parse as an option. Run one search per term:
  `git -C <marketplace-root> grep -n -F -e '<term>' origin/<default-branch> -- <entity-path>`.
  **Every** term must match for C to pass; the first term with no match is a Precondition C failure
  (same routing as any other C failure). Quote one matching line per term in the eventual push-gate
  display.

Any failing precondition for a given repo → skip that repo, record it in the deferred TODO (9c.7),
continue with the rest.

**9c.3 — Sequencing gate, asked ONCE per run**, before any worktree is created: show the mechanical
Precondition-A check results, then require an explicit `yes` (not "sure", not silence) to proceed.
Anything else → stop, write the deferred TODO, touch nothing in any other repo. If Precondition A's
checks already show a failure, skip the question and defer directly. Exact prompt wording: 9c.3 in
`references/cleanup-and-provenance.md`.

**9c.4 — Per-repo mechanism**, processed sequentially in ascending absolute-path order (stable
reports; one STOP never aborts the rest): preflight (clean-tree check on the target file; resolve and
fetch the actual default branch — never assume `main`/`master`; STOP and ask the user if it can't be
resolved or the fetch fails); branch `<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>` (see
`--branch-prefix` in Arguments), same name across every repo touched this run; delegate worktree
creation to the target marketplace's own worktree-management skill if one exists, else `git worktree
add` directly and note the degraded path; surgical edit — remove the promoted section, insert/extend
the pointer per 9c.5, touch nothing else, verified by `git status --porcelain`; one commit per repo
(explicit `git add <path>`, never `-A`/`.`); push gate (9c.8); PR creation via the detected host's
tooling (`gh`/GitHub MCP for GitHub, following `dev-essentials:github-mcp-conventions`, or a manual
pushed-branch-plus-PR-text fallback otherwise). Exact commands and prompt text: 9c.4 in
`references/cleanup-and-provenance.md`.

**9c.5 — Pointer template.** Extend — never duplicate — a
`## Cross-project rules — migrated to marketplace skills` heading with one bullet per promoted rule,
carrying a load-bearing one-line gist (graceful degradation for anyone who hasn't updated their plugin
yet, not decoration). Only fall back to an inline stub-in-place when the removed heading is referenced
elsewhere in the repo — grep for it first. Exact template: 9c.5 in
`references/cleanup-and-provenance.md`.

**9c.6 — Dirty-repo handling.** Hard STOP with no override for: the target file itself
modified/staged/conflicted, a rebase/merge/cherry-pick in progress, detached or unborn HEAD, target
file untracked (route to 9c.0's other branch instead), or worktree creation failing for any reason.
Unrelated dirt elsewhere in the repo: report and ask once, default to skip. Never force-push, amend,
rebase, stash, or checkout-discard anything in repo B beyond the target file; never touch
`.gitignore` or `.claude/settings.json` there. Full matrix: 9c.6 in
`references/cleanup-and-provenance.md`.

**9c.7 — Deferred TODO.** Write one artifact in the CALLING repo (wherever this skill was invoked
from) — apply Phase 10's own propose-then-confirm pattern to this artifact too: propose a default
path (next to wherever `--report=<path>` would otherwise go, or a sensible default like
`.claude-audit-todo-<date>.md` in the current working directory if no other convention exists) and
ask for confirmation; if the user declines a file, print the full TODO content inline in chat
instead. Because `--resume=<path>` reads a file and nothing else, the user must save that block
verbatim to a file themselves and pass that path as `--resume=<path>`; until they do, this deferred
promotion cannot be resumed. Listing, repo-level: absolute root, remote URL, base
branch, planned branch name (`<branch-prefix>/chores/claude-md-promotion-<YYYYMMDD>`), the
marketplace repo root (absolute path or resolvable identifier), the marketplace repo's own remote URL
(`Marketplace remote` — validated on resume against the resolved `<marketplace-root>`, per
Precondition A above), the promoted commit SHA (`this-run-marketplace-head-sha`), and which
precondition/answer blocked it — repo-level reasons (a B failure, a dirty-repo skip, the sequencing
gate declined, `--cross-repo` off) stand as-is, but when the reason is an A or C failure (both
per-promotion, not repo-level), name the specific `<plugin>:<entity>@<version>` it applies to inline,
e.g. "precondition C failure for dev-essentials:foo@1.2.0". Then, one `<plugin>:<entity>@<version>` sub-block per pending edit
landing in that repo (9c.9's batching rule — multiple promoted sections in one repo share the single
commit, but each still needs its own sub-block): target file, entity path (relative to `Marketplace
root`), load-bearing terms (Precondition C's input, re-run fresh on resume rather than trusted from a
stale captured quote), the verbatim section to remove, and the exact pointer bullet(s).
**Written on every run where `--cross-repo=off` (the default) caused a cross-repo-sourced promotion to
defer, not only when `--cross-repo` was set but failed a gate** — this is what makes the 9c-only
re-entry mode (9c.1) usable on a later, separate invocation. Resumable later via
`--resume=<path> --cross-repo=<repo|all>` without re-running the whole audit — resume never jumps
straight to 9c.4: it re-enters at 9c.2 (re-checking the three preconditions against current state,
since time has passed, using whatever marketplace root Phase 0 already resolved for this run — see
Phase 0 — and reading the promoted commit directly from the persisted `Promoted commit` field), then
re-runs 9c.3's sequencing confirmation once for the resumed set, and only then proceeds to 9c.4.
Phase 5's approval gate is NOT re-run — approvals are carried over from the original run's TODO
artifact.

**9c.8 — Verbatim push gate per repo**, showing: repo root and remote, branch, worktree path, commit
sha and subject, diff stat, removed section heading(s), pointer(s) added, the Precondition-C coverage
quotes (one matching line per load-bearing term, always re-derived fresh — never a stale captured
quote), the Precondition-B "plugin enabled: yes" confirmation, and the planned PR's source/target and
linked-issue status — then asking explicitly: "Push this branch and open a PR? (yes / no /
push-only)". `no` = stays local, reported as prepared-but-unpushed. `push-only` = push without opening
a PR. There is no separate pre-edit confirmation — the edit lands in an isolated worktree, invisible
until push — so this diff-bearing gate is the one decision point per repo.

**9c.9 — Guardrails specific to this sub-phase** (full list: 9c.9 in
`references/cleanup-and-provenance.md`): the flag is not a pre-authorization; sequencing (9c.2 + 9c.3)
is absolute, no exception for "it's just docs"; one repo means one worktree/branch/commit/PR; never
force past a dirty product repo; no hard dependency on any specific host's tooling; pointers always
keep a one-line gist.

#### 9d — Personal entities: commands/agents/skills (default: report-only)

Applies to personal global commands, agents, and skills under
`<claude-root>/{commands,agents,skills}` that were fully superseded by an entity promoted or
E-fixed this run (Phase 6 output), or classified **F-stale** by Phase 3 because an already-shipped
marketplace entity supersedes them (not F-stale for an unrelated reason).

Default: list each superseded personal file with a suggested manual action — edit it to reference the
new marketplace entity instead of its own duplicated content, or delete it outright — plus how to
resume (re-run with `--scope=personal-entities --delete-personal-entities`), in the Phase 10 report's
"Manual TODOs" list, the same shape already used for a project-repo CLAUDE.md file when `--cross-repo`
is off. Nothing is deleted or edited under this default. The two eligibility routes recover
differently: a promoted/E-fixed-this-run deferral becomes reachable once the marketplace PR merges (a
later run then reclassifies the file F-stale-because-already-shipped and takes that branch of the
gates below); an already-shipped/F-stale deferral needs no PR merge — just re-run the audit directly.
Full rationale: `references/cleanup-and-provenance.md`.

**Partially-superseded wrapper case.** A wrapper whose personal layer is genuinely still needed (per
`references/classification-framework.md` Step 4's orthogonality rule — it legitimately keeps its
B-taste or pure-forwarding sections) but which also now carries an F-stale section (a divergence
already fixed upstream, per Step 4's own "verify the self-label against actual current content"
rule) is **never eligible for deletion**, even with `--delete-personal-entities`. This grounds in
the skill's existing Phase 9a partial-promotion rule — "never stub a partially-promoted file,
annotate only the promoted section" — applied here to a wrapper instead of a memory file:
report-only, naming the specific section(s) to trim and the shipped entity+version that now covers
each. The two-recovery-routes structure mirrors 9d's own above: a wrapper section whose fix was
E-fixed by an EARLIER run is already reachable for trimming now; a wrapper section whose fix
landed THIS run only becomes trimmable once that promotion is published (same publish-check gates
as the fully-superseded case below).

With `--delete-personal-entities` (bare boolean, opt-in), three gates run in order before any file
is removed:

1. **Automated publish and local-load verification**, before any human prompt is shown: re-run 9c.2's
   Preconditions A and C against the target marketplace. For a **promoted/E-fixed this run** file, A
   runs in full — including its ancestor-check-failure fallback — against this run's own Phase 8 bump.
   For an **already-shipped/F-stale** file, there is no this-run commit to check against: A still
   resolves and fetches the default branch under the same fallback and fetch-failure rules, but skips
   the ancestor check and the version-floor check, leaving only the existence check (`cat-file -e
   origin/<default-branch>:<entity-path>`). Precondition C is unchanged either way: run per superseded
   personal file, at the same ref, against that file's own load-bearing terms. There is no *repo-side*
   equivalent of Precondition B here — personal entities aren't tied to any target repo — but its
   caller-side counterpart applies: grep the caller's own `<claude-root>/settings.json` (and/or the
   global `<claude-root>/CLAUDE.md` "Prerequisites" section) for the target marketplace name plus the
   owning plugin being registered or enabled. If not registered, do NOT delete — report enabling the
   plugin locally as a prerequisite instead.
2. **A once-per-run marketplace-publish confirmation**, in the same "has this been merged, are you
   ready?" style as 9c.3's sequencing gate for the promoted/E-fixed branch; for the already-shipped/
   F-stale branch, publication is already proven by step 1's checks, so the wording shifts to a
   readiness-only confirmation. Both branches still ask this gate once per run — a run whose scope
   mixes both routes asks once, using the stricter promoted/E-fixed wording, covering every file in
   scope. Exact prompts: `references/cleanup-and-provenance.md`.
3. **An individual per-file `yes` immediately before each deletion**, carrying step 1's matching
   Precondition-C grep lines as required coverage quotes — one matching line per load-bearing term,
   as 9c.8 does for its push gate.

A failure in step 1, or a `not yet` in step 2, falls back to the report-only default for every
personal entity file in scope this run — and on a step-1 failure no deletion prompt is shown at all,
the same way 9c.3 skips its own question when Precondition A has already failed. A `no` in step 3
falls back to report-only for that file only. Full mechanics, templates, and exact prompt wording
live in `references/cleanup-and-provenance.md`.

### Phase 10 — Report

Default in-chat. This skill makes no assumption that a `Notes/Plans` / `Notes/Results` convention
exists in the calling repo — only write a file if `--report=<path>` names one, or if the calling
repo obviously already has its own such convention, in which case propose the path for confirmation
rather than assuming it.

```markdown
# Personal-convention audit — run report

## Scope

<scope tokens> · <p> projects (<w> worktree siblings collapsed) · target marketplace <name> @ <branch>

## Triage outcome

| Disposition | Candidates | Approved | Deferred | Rejected |
|---|---|---|---|---|

## Shipped this run

| Entity | Kind | Plugin | Rules folded in (#) | Files |
|---|---|---|---|---|

If any row above is a brand-new entity (C/D disposition, not an E-fix edit to something already
shipped), append this line — per Phase 8's restart notice:

> **Restart required for new entities.** `<entity>` is brand-new this run. After the promotion PR
> merges, `/plugin marketplace update` + `/reload-plugins` will not make it invocable — those
> refresh hooks/MCP/LSP live but do not rebuild the slash-command index for entities that did not
> exist before. A full Claude Code restart is required. (Entities that were only edited/fixed in
> place don't need this — `/reload-plugins` alone picks those up — though restarting is always
> safe.)

## Review loop

<rounds> · findings by severity · APPLY/PARTIAL/REJECT counts · final verdict

## Version

<plugin> <old> -> <new> (<MAJOR|MINOR|PATCH>) — one bump, <reason>

## Source-side cleanup

| File | Action | Confirmed |
|---|---|---|

Manual TODOs:

- <repo>: <what to remove/replace>, and how to resume

## Deferred and rejected (carried to next run)

| # | Disposition | Rule | Why not now |
|---|---|---|---|

## Commits

<sha> <subject>   (local only — nothing pushed unless a Phase 9c push-gate said yes)
```

**Never push the target marketplace's own commits either, unless the user explicitly says so
elsewhere in the session.**

## Guardrails

- Only `--autonomous` skips a Phase 9 gate (see Arguments). Phase 5 follows "Autonomy".
- No hardcoded marketplace or host name anywhere in this skill's own text, prompts, or examples,
  except to name the source marketplace of an external, optional tool referenced in prose — that
  identifies a dependency's provenance, not the promotion target, and not this skill's own shipping
  marketplace.
- Classify per rule, not per file — a single source file routinely mixes dispositions.
- `type:` frontmatter is never a category signal by itself; content must be read.
- Corroboration count is the strongest promote signal — always check it before proposing a new
  entity.
- An **E** disposition is never a new entity. It is always a fix to an existing shipped entity,
  followed by pruning the source.
- Never auto-edit a project-repo CLAUDE.md without `--cross-repo`.
- Never push without an explicit per-repo yes, even with `--cross-repo` set. `--autonomous` counts as that yes.
- Never delete a personal entity file without `--delete-personal-entities`, its automated
  publish-and-local-load verification check, the once-per-run marketplace-publish gate, and its own
  individual per-file confirmation.
- Never touch a file outside an approved item's own provenance list.
- A wrapper personal entity is never assigned a disposition without a completed full-text diff
  against its wrapped entity.

## References

| File | When to read |
| --- | --- |
| `references/source-inventory.md` | The full twelve-item structural-landmine list (discovery paths and the decode/probe/collapse procedure live inline in SKILL.md Phase 1, since they apply on every run). |
| `references/classification-framework.md` | Phase 3 full decision tree, tie-breakers, and calibration mini-cases. |
| `references/entity-authoring-conventions.md` | Phase 6 authoring rules: entity-kind selection, frontmatter, body structure, commit discipline. |
| `references/cleanup-and-provenance.md` | Phase 9 templates and the full Phase 9c cross-repo mechanism, gate text, and dirty-repo matrix. |

## Examples

| File | When to read |
| --- | --- |
| `examples/full-audit-walkthrough.md` | End-to-end run: invocation, triage, partial approval, authoring, review, version bump, all four Phase 9 sub-phases (including the 9c-only resume re-entry on a later invocation). |
| `examples/fix-shipped-entity.md` | The E-disposition path specifically, two worked cases, end to end. |

## Cross-references

| Skill | Relationship |
| --- | --- |
| `dev-essentials:review-loop` | Used in Phase 7 when the target marketplace is this one. Never a hard dependency — if the target marketplace lacks an equivalent, Phase 7 degrades to a single-pass self-review and says so. |
| `dev-essentials:subagent-orchestration` | Governs dispatch discipline throughout any multi-step work this skill delegates. If unavailable in the target marketplace, dispatch decisions (concurrent multi-`Agent`-call batching, brief discipline) are made ad hoc. |
| `dev-essentials:git-worktree-management` | Used in Phase 9c for worktree creation when the target marketplace ships it. If absent, Phase 9c creates the worktree directly with `git worktree add` and notes the degraded path explicitly. |
| `dev-essentials:git-sync` | Precedent for the "never push by default" push-gate wording used throughout Phase 9 and Phase 10. |
| `dev-essentials:github-mcp-conventions` | Used in Phase 9c.4 step 7 when a cross-repo target's remote is GitHub and `gh`/GitHub MCP tooling is available — governs owner/repo passthrough and pagination discipline for the PR-creation call. If absent or the host differs, Phase 9c.4 falls back to a manual PR-creation report. |
| `dev-essentials:write-markdown` | Applied whenever this skill authors or edits markdown — new entities in Phase 6, pointer edits in Phase 9 — to keep the result markdownlint-clean on the first write. |
