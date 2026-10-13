# Classification Framework — Phase 3 Decision Tree

Referenced by Phase 3 of `SKILL.md`. All disposition tokens used in this file match the six-value
enum in `SKILL.md` verbatim. Do not invent new tokens.

---

## The six dispositions

| Disposition | Meaning | Output of Phase 6 |
| --- | --- | --- |
| **A-local** | Genuinely project-local; no promotion value. | Nothing — leave in place. |
| **B-taste** | Personal preference with no external anchor, unless demonstrably an established team codestyle with named evidence. | Nothing — leave in place. |
| **C-universal** | Corroborated, externally-anchored, and scope-free. | A new entity, unscoped. |
| **D-scoped** | Corroborated and externally-anchored, but only within a stated product/framework/pipeline scope. | A new entity, with the scope stated in its own description. |
| **E-fix-shipped** | The rule is actually a correction to something an already-shipped entity gets wrong. | An edit to the existing shipped entity; the source is then pruned. Never a new entity. |
| **F-stale** | The source content is outdated, superseded, or a dangling index/index-adjacent artifact. | Prune or annotate; no new content. |

---

## Step 1 — Corroborate first

Before classifying any single rule, group it with every other extracted rule (from any source type,
any project) that states an equivalent point. Count the number of **independent sources** in the
cluster — independent meaning distinct files, not distinct lines within one file. One exception:
memory files that are the same repository's memory re-accumulated across collapsed git-worktree
siblings count once for the whole family, not once per file (see SKILL.md Phase 1's worktree-sibling
collapse).

- **3 or more independent sources stating an equivalent rule is a strong promote signal** —
  corroboration this wide is unlikely to be one person's local habit.
- A single-source rule can still be promoted (C/D) if step 3's external-authority test clearly
  applies — corroboration is the strongest signal, not the only one.
- `--min-evidence=<N>` filters the candidates presented in Phase 4 to clusters with at least `N`
  independent sources; it does not change the classification itself, only which candidates surface.

## Step 2 — Check already-promoted status against on-disk manifests

Before proposing a new entity, verify the rule is not already shipped somewhere in the target
marketplace:

- Grep the actual **on-disk plugin manifests** (each plugin's `.claude-plugin/plugin.json` plus its
  skills/agents/commands directories) in the target marketplace repo — never trust a memory index's
  own "migrated" claim (landmine 7 in `references/source-inventory.md` — indexes go stale) and never
  trust the session's runtime skills listing (it mixes the user's personal global skills in with the
  target marketplace's actual shipped skills, and file location — not the listing — is what
  distinguishes them).
- Distinguish "personal command/agent/skill under `<claude-root>/{commands,agents,skills}/`" from
  "shipped entity under `<marketplace-root>/<plugin>/{commands,agents,skills}/`" strictly by
  which of those two directory trees the file lives in.
- If the rule is already shipped and correctly reflected there, disposition is **F-stale** (prune
  the now-redundant personal source) rather than C/D — when the redundant source is itself a personal
  entity file (command/agent/skill), that pruning routes through Phase 9d's delete flow (report-only
  by default; deletion only under `--delete-personal-entities`) rather than a plain memory-file prune.
- If the rule is already shipped but the shipped version is *wrong*, disposition is **E-fix-shipped**
  (see Step 4).

## Step 3 — B-vs-C external-authority tie-breaker

Ask one question: **does the rule cite an external authority?** An external authority is any of: a
static analyzer or compiler diagnostic, a shared package's documented contract, a documented
convention (style guide, RFC, official docs), or an existing skill/entity the rule builds on or
corrects.

- **Cites an external authority → C or D.** The rule is anchored to something outside one person's
  preference, which is what makes it defensible to a stranger reading the shipped entity later.
- **Only asserts a preference, no external anchor → B.** Leave it as personal taste, unless the user
  can name specific evidence that it is an established **team** codestyle (not just their own
  preference) — in which case treat that named evidence itself as the external authority and
  reclassify as C/D.

**This tie-breaker is applied per rule, never per section.** A single CLAUDE.md section commonly
mixes a B rule and a C rule back to back (see calibration case 2 below) — classifying the whole
section by its first or dominant rule misfires on the other rule in the pair.

## Step 4 — `E` disposition and its marker phrase

**E-fix-shipped never produces a new entity.** The fix always lands as an edit to the existing
shipped entity's own files; the source that reported the problem is then pruned (Phase 9a), because
its content is now folded into the shipped entity's corrected version.

The near-certain marker for E is language like **"stopgap until `<plugin>:<entity>` is updated"** —
a memory file or wrapper personal entity that explicitly frames itself as a temporary workaround
for a known defect in a shipped entity is self-identifying as E. Do not take the self-label or
stated delta at face value without verifying the described defect against the shipped entity's
actual current content — the defect may already have been fixed by an unrelated change, in which
case the disposition becomes F-stale (prune, nothing to fix) instead of E.

The second common path to E is the wrapper-entity landmine (`references/source-inventory.md`,
landmine 12): a personal command/agent/skill's stated "delta" against the shipped entity it wraps
turns out, once diffed against the base entity's actual current content, to be a correction of
something the base entity states incorrectly (e.g. a wrong field name, an outdated command flag)
rather than a genuine personal addition.

**Wrapper-intentionality and E-extraction are orthogonal.** A wrapper that legitimately stays
personal forever — argument forwarding, an opt-out flag, a preference sourced from the user's own
global config — can simultaneously carry a genuine base-entity correction in a different section of
the same file. "The wrapper is intentional" is never a reason to skip diffing it against the entity
it wraps: this is the same "classify per rule, not per file" principle from Step 3 above (calibration
case 2), applied to a wrapper file instead of a CLAUDE.md section. The diff decides per DIVERGENCE,
not per file — a wrapper can be simultaneously "keep forever" for one section and "extract this
section as E" for another.

### Wrapper divergences use the same rules, no new taxonomy

Classify each wrapper divergence with the same Step 3/4 rules already used for every other rule
source in this skill — no wrapper-specific taxonomy is needed. The only wrapper-specific addition
is: a pure-forwarding/boilerplate divergence (argument passthrough, the wrapper's own flag parsing)
produces no Phase 2 record at all — it isn't a rule. A divergence that supplies a step the base
entity should own but omits, where the omission is wrong for every consumer, is also E — reached
via Step 7's overlap branch: extend the base entity rather than creating a near-duplicate.

## Step 5 — `type:` frontmatter is never a category signal

A memory file's `type:` frontmatter field (however it is shaped — see landmine 1 in
`references/source-inventory.md`) **predicts nothing about disposition, in either direction**.
Content must be read regardless.
Two real, opposite-direction findings anchor this rule (see calibration cases 3 and 4 below):

- A file self-labelled `type: reference` turned out to be pure A-local trivia.
- A file self-labelled `type: project` turned out to be a clean D-scoped framework gotcha.

Never pre-filter by `type:` to save time — the signal does not exist.

## Step 6 — Over-generalization screen

Before accepting a rule that reads as universal ("always do X"), check its own supporting evidence
for scope leakage:

- Is the rule's only sanctioned exception really just one specific pipeline's internal stage
  numbering, dressed up as a general exception clause?
- Does the rule's entire worked example list consist of one pipeline's own internal artifact names,
  presented as if they were generic illustrations?

When either is true, the rule is "one incident in a trench coat" — a single real incident that has
been over-generalized into a universal principle. The remedy is not to reject the rule, but to:

1. Generalize the underlying principle (state it independent of the one pipeline's specifics).
2. Keep the original incident as a labelled worked example (not the sole justification).
3. Hedge the scope explicitly in the new entity's description, rather than presenting a
   one-incident rule as universal (D-scoped instead of C-universal, if the hedge cannot be removed).

## Step 7 — Gap-vs-overlap check

Before proposing any brand-new entity, check the target marketplace's existing entities for the
same capability:

- **Gap** — no existing entity covers this; a new entity is justified.
- **Overlap** — an existing entity already covers this territory, even if incompletely; extend that
  entity (an additional `## Rule N` section, an additional reference file) rather than creating a
  near-duplicate that will drift from the original over time.

This check is the same discipline described for skill authoring in
`references/entity-authoring-conventions.md` — do it here, before Phase 4 proposes the destination,
not after Phase 6 has already started authoring.

---

## Calibration mini-cases

Sanitized, generalized versions of real findings. Repo/product names are genericized.

### Case 1 — Corroboration wins

A rule ("write all commit messages and code comments in English regardless of the chat language")
appeared, independently worded, in: the global CLAUDE.md, three different repos' own CLAUDE.md
files, and one memory file. Five independent sources for the same point. Classified **C-universal**
on corroboration alone, even though a single instance of this rule, read in isolation, might have
looked like ordinary house style rather than something worth a shared entity.

### Case 2 — Classify per rule, not per section

A single CLAUDE.md section titled "Working with the assistant" contained three adjacent bullet
points: (1) a model-selection cost/capability matrix (which model tier for which kind of task), (2)
a preference for terse, single-line commit-message subjects over multi-paragraph bodies even though
the repo's own history mixes both styles, and (3) a rule that a subagent dispatch must include a
fully self-contained brief, because the subagent does not see the parent conversation.

Point (1) read as ordinary **B-taste** the first time this section was audited — a preference about
cost vs. capability trade-offs with no external authority behind the specific tiers chosen. A later
audit of the same section, run after that exact matrix had since been promoted into
`dev-essentials:subagent-orchestration`'s "Model selection" section, reclassified it as
**F-stale** per Step 2's already-promoted-manifest check: the personal source is now redundant with
a correctly-reflected shipped entity, so it is pruned rather than re-promoted or left as B. Point (2)
is genuine **B-taste** — nothing about "single-line vs. multi-paragraph" commit subjects is dictated
by a linter, style guide, or existing entity, so it stays personal. Point (3) is
**C-universal** — it cites the external, verifiable fact that a subagent starts in its own
context window without the parent conversation, which is a platform behavior, not a preference.
Classifying the whole section as one disposition would have wrongly re-promoted the now-stale matrix, wrongly promoted the
commit-style preference, or wrongly suppressed the self-contained-brief rule.

### Case 3 — `type: reference` that was pure A-local trivia

A memory file self-labelled `type: reference` documented which git branch names mapped to which
internal release-tag scheme for one specific repository. Despite the "reference" label suggesting
generally-useful lookup content, the content was entirely specific to that one repo's own
branch/tag history. Classified **A-local**. The `type:` field predicted nothing.

### Case 4 — `type: project` that was a clean D-scoped gotcha

A different memory file, self-labelled `type: project` (a label that suggests project-specific
scope), documented a real workaround for an ORM behaving incorrectly against a specific NoSQL
provider — a gotcha that would recur for anyone using that same ORM-against-provider combination in
any repo, not just the one where it was first hit. Classified **D-scoped** (scope: that ORM against
that provider). The `type:` field again predicted nothing — this time in the opposite direction
from Case 3.

### Case 5 — Two `E` cases found two different ways

- A memory file self-labelled "stopgap until `<plugin>:<some-shipped-skill>` is updated" documented
  that the shipped skill's own worked example used an incorrect code pattern for a specific API call.
  Classified **E-fix-shipped**: the shipped skill's example was corrected, and the memory file was
  then pruned rather than becoming its own entity.
- A wrapper personal command's stated "delta" against the shipped entity it wraps — found only by
  diffing the wrapper's body against the current content of the base entity, not by reading the
  wrapper alone — turned out to be a correction to a wrong field name the base entity's own
  instructions told the reader to use. Classified **E-fix-shipped** for the same reason: the
  correction belongs in the base entity, not in a new wrapper-derived entity.

### Case 6 — Reconcile drift, don't pick a copy

A roughly six-section project-preamble template had been copy-pasted, with drift, across four
CLAUDE.md files in three different repos — each copy had picked up small local edits over time. In
one of those repos, the root `CLAUDE.md` and its nested `.claude/CLAUDE.md` overlapped roughly 90%,
with the nested file being a stale superset that had not been kept in sync with edits made to the
root file. The correct promotion candidate was the **reconciled** template — merging the drifted
copies into one canonical version — not any single copy picked because it happened to be the most
recently edited or the most complete-looking. Classified **C-universal** for the reconciled result;
the four source copies (five including the stale nested superset) each get a `source:` citation
into the same cluster.
