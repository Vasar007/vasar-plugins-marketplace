# Classification Framework — Phase 3 Decision Tree

Phase 3 of `SKILL.md` reads this file. All disposition tokens in this file match the enum in `SKILL.md` verbatim. Do not invent new tokens. The file holds the dispositions, Steps 1 to 7, and the calibration cases.

## Contents

- The dispositions
- Step 1: Corroborate first
- Step 2: Check already-promoted status against on-disk manifests
- Step 3: B-vs-C external-authority tie-breaker
- Step 4: `E` disposition and its marker phrase
- Step 5: `type:` frontmatter is never a category signal
- Step 6: Over-generalization screen
- Step 7: Gap-vs-overlap check
- Calibration mini-cases

---

## The dispositions

| Disposition | Meaning | Output of Phase 6 |
| --- | --- | --- |
| **A-local** | Truly project-local. No promotion value. | Nothing. Leave it in place. |
| **B-taste** | Personal preference with no external anchor. Exception: named evidence shows an established team code style. | Nothing. Leave it in place. |
| **C-universal** | Corroborated, externally anchored, and free of scope. | A new entity, unscoped. |
| **D-scoped** | Corroborated and externally anchored, but only within a stated product, framework, or pipeline scope. | A new entity, with the scope stated in its own description. |
| **E-fix-shipped** | The rule corrects something that an already-shipped entity gets wrong. | An edit to the existing shipped entity. Then the run prunes the source. Never a new entity. |
| **F-stale** | The source content is outdated, superseded, or a dangling index or index-adjacent artifact. | Prune or annotate. No new content. |

---

## Step 1 — Corroborate first

Before you classify a rule, group it with every other extracted rule that states an equivalent point, from any source type and any project. Count the **independent sources** in the cluster. Independent means distinct files, not distinct lines in one file. One exception covers collapsed git-worktree siblings. Their memory indexes hold the memory of one repository, accumulated again. They count once for the whole family, not once per file (see `references/source-inventory.md`, worktree-sibling collapse).

- **3 or more independent sources that state an equivalent rule are a strong promote signal**. Corroboration this wide is unlikely to be the local habit of one person.
- If the external-authority test of Step 3 clearly applies, a single-source rule can still be promoted (C/D). Corroboration is the strongest signal, not the only one.
- `--min-evidence=<N>` filters the candidates that Phase 4 presents to clusters with at least `N` independent sources. It does not change the classification. It changes only which candidates the triage shows.

## Step 2 — Check already-promoted status against on-disk manifests

Before you propose a new entity, find out whether the target marketplace already ships the rule:

- Grep the real **on-disk plugin manifests** in the target marketplace repo: the `.claude-plugin/plugin.json` of each plugin, plus its `skills/`, `agents/`, and `commands/` directories. Never trust the "migrated" claim of a memory index. Indexes go stale (landmine 7 in `references/source-inventory.md`). Never trust the runtime skills listing of the session either. It mixes the personal global skills of the user with the shipped skills of the target marketplace. Only the file location tells them apart.
- Tell a personal command, agent, or skill under `<claude-root>/{commands,agents,skills}/` from a shipped entity under `<marketplace-root>/<plugin>/{commands,agents,skills}/` strictly by the directory tree that holds the file.
- If the rule is already shipped and correctly reflected there, the disposition is **F-stale** (prune the personal source, which is now redundant), not C/D. The redundant source can be a personal entity file (command, agent, or skill). Then the prune goes through the delete flow of Phase 9d, not through a plain rule-file prune. That flow is report-only by default, and it deletes only with `--delete-personal-entities`.
- If the rule is already shipped but the shipped version is *wrong*, the disposition is **E-fix-shipped** (see Step 4).

## Step 3 — B-vs-C external-authority tie-breaker

Ask one question: **does the rule cite an external authority?** An external authority is one of these:

- A static analyzer or a compiler diagnostic.
- The documented contract of a shared package.
- A documented convention (style guide, RFC, official docs).
- An existing skill or entity that the rule builds on or corrects.

The answer decides between B and C:

- **Cites an external authority → C or D.** The rule rests on something outside the preference of one person. That makes it defensible to a stranger who reads the shipped entity later.
- **Only asserts a preference, with no external anchor → B.** Leave it as personal taste. Exception: the user names specific evidence that the rule is an established **team** code style, not only their own preference. Then treat that named evidence as the external authority, and reclassify the rule as C/D.

**Apply this tie-breaker per rule, never per section**. One CLAUDE.md section often mixes a B rule and a C rule back to back (see calibration case 2 below). A classification of the whole section by its first or dominant rule gives the other rule of the pair the wrong disposition.

## Step 4 — `E` disposition and its marker phrase

**E-fix-shipped never produces a new entity.** The fix always lands as an edit to the files of the existing shipped entity. Then Phase 9 prunes the source that reported the problem. It uses 9a, 9b, 9c, or 9d, by the source type. The corrected shipped entity now holds the content of that source.

The near-certain marker for E is text like **"stopgap until `<plugin>:<entity>` is updated"**. Some rule files and wrapper personal entities call themselves a temporary workaround for a known defect in a shipped entity. Such a file identifies itself as E. Do not accept the self-label or the stated delta as it stands. Read the current content of the shipped entity, and find out whether the defect is still there. Sometimes an unrelated change already fixed it. In that case, the disposition is F-stale (prune, nothing to fix), not E.

The second common path to E is the wrapper-entity landmine (`references/source-inventory.md`, landmine 12). A personal command, agent, or skill states a delta against the shipped entity that it wraps. The diff against the current content of the base entity shows that the delta is a correction. The base entity states something wrong, for example a wrong field name or an outdated command flag. It is not a real personal addition.

**Wrapper-intentionality and E-extraction are orthogonal.** A wrapper can stay personal forever for good reasons: argument forwarding, an opt-out flag, or a preference from the global configuration of the user. The same file can still carry a real correction of the base entity in another section. "The wrapper is intentional" is never a reason to skip the diff against the entity that it wraps. This is the principle "classify per rule, not per file" of Step 3 (calibration case 2). Here it applies to a wrapper file, not to a CLAUDE.md section. The diff decides per DIVERGENCE, not per file. One wrapper can be "keep forever" for one section and "extract this section as E" for another.

### Wrapper divergences use the same rules, no new taxonomy

Classify each wrapper divergence with the rules of Steps 3 and 4, the same as every other rule source of this skill. A wrapper needs no taxonomy of its own. There is one addition for wrappers. A pure forwarding or boilerplate divergence gives no Phase 2 record at all, because it is not a rule. Examples are argument passthrough and the flag parsing of the wrapper. A divergence can also supply a step that the base entity must own but leaves out, where the gap is wrong for every consumer. That divergence is also E, through the overlap branch of Step 7: extend the base entity, and do not create a near-duplicate.

## Step 5 — `type:` frontmatter is never a category signal

The `type:` frontmatter field of a rule file **predicts nothing about the disposition, in either direction**, whatever its shape (see landmine 1 in `references/source-inventory.md`). Always read the content. Two real findings in opposite directions anchor this rule (see calibration cases 3 and 4 below):

- A file with the self-label `type: reference` was pure A-local trivia.
- A file with the self-label `type: project` was a clean D-scoped framework gotcha.

Never pre-filter by `type:` to save time. The signal does not exist.

## Step 6 — Over-generalization screen

A rule can read as universal ("always do X"). Before you accept it, look in its own supporting evidence for scope leakage:

- Is the only sanctioned exception of the rule really the internal stage numbering of one pipeline, dressed up as a general exception clause?
- Is the whole worked-example list of the rule made of the internal artifact names of one pipeline, shown as generic illustrations?

If either answer is yes, the rule is "one incident in a trench coat": a single real incident, over-generalized into a universal principle. Do not reject the rule. Instead:

1. Generalize the underlying principle. State it without the specifics of the one pipeline.
2. Keep the original incident as a labeled worked example, not as the sole justification.
3. Hedge the scope explicitly in the description of the new entity. Do not present a one-incident rule as universal. If you cannot remove the hedge, use D-scoped instead of C-universal.

## Step 7 — Gap-vs-overlap check

Before you propose a new entity, look for the same capability in the existing entities of the target marketplace:

- **Gap**: no existing entity covers it. A new entity is justified.
- **Overlap**: an existing entity already covers this territory, at least in part. Extend that entity (an additional `## Rule N` section, an additional reference file). Do not create a near-duplicate, because it drifts from the original over time.

`references/entity-authoring-conventions.md` of `promote-conventions` applies the same check in Phase 6. Do it here first, before Phase 4 proposes the destination, not after Phase 6 starts authoring.

---

## Calibration mini-cases

Sanitized and generalized versions of real findings. The repo and product names are generic.

### Case 1 — Corroboration wins

A rule ("write all commit messages and code comments in English regardless of the chat language") appeared, in independent words, in five sources: the global CLAUDE.md, the CLAUDE.md files of three different repos, and one rule file. Classified **C-universal** on corroboration alone. Read alone, one instance of this rule can look like ordinary house style, not like something worth a shared entity.

### Case 2 — Classify per rule, not per section

One CLAUDE.md section titled "Working with the assistant" held three adjacent bullet points:

1. A model-selection matrix of cost and capability (which model tier for which kind of task).
2. A preference for terse, single-line commit subjects over multi-paragraph bodies, although the history of the repo mixes both styles.
3. A rule that each subagent dispatch must include a fully self-contained brief, because the subagent does not see the parent conversation.

The first audit of this section read point 1 as ordinary **B-taste**: a preference about the trade-off of cost and capability, with no external authority behind the chosen tiers. Later, that exact matrix was promoted into the "Model selection" section of `dev-essentials:subagent-orchestration`. A later audit of the same section then reclassified point 1 as **F-stale**, by the already-promoted manifest check of Step 2. The personal source is now redundant with a correctly reflected shipped entity, so the run prunes it. It does not promote it again or leave it as B. Point 2 is real **B-taste**. No linter, style guide, or existing entity dictates single-line or multi-paragraph commit subjects, so it stays personal. Point 3 is **C-universal**. It cites an external fact that anyone can test: a subagent starts in its own context window without the parent conversation. That is a platform behavior, not a preference. One disposition for the whole section gets at least one point wrong. It promotes the stale matrix again, promotes the commit-style preference, or suppresses the self-contained-brief rule.

### Case 3 — `type: reference` that was pure A-local trivia

A rule file with the self-label `type: reference` documented which git branch names map to which internal release-tag scheme of one specific repository. The "reference" label suggests generally useful lookup content. But the content was specific to the branch and tag history of that one repo. Classified **A-local**. The `type:` field predicted nothing.

### Case 4 — `type: project` that was a clean D-scoped gotcha

Another rule file had the self-label `type: project`, a label that suggests project-specific scope. It documented a real workaround for an ORM that behaves wrong against a specific NoSQL provider. The gotcha recurs for anyone who uses that ORM with that provider, in any repo, not only in the repo where it first came up. Classified **D-scoped** (scope: that ORM against that provider). The `type:` field again predicted nothing, this time in the opposite direction from Case 3.

### Case 5 — Two `E` cases found two different ways

- A rule file with the self-label "stopgap until `<plugin>:<some-shipped-skill>` is updated" documented a defect. The worked example of the shipped skill used a wrong code pattern for a specific API call. Classified **E-fix-shipped**. The run corrected the example of the shipped skill, and then pruned the rule file. The file did not become its own entity.
- A wrapper personal command stated a delta against the shipped entity that it wraps. Only the diff of the wrapper body against the current content of the base entity found the problem. A read of the wrapper alone did not. The delta corrected a wrong field name that the instructions of the base entity told the reader to use. Classified **E-fix-shipped** for the same reason: the correction belongs in the base entity, not in a new entity derived from the wrapper.

### Case 6 — Reconcile drift, don't pick a copy

A project-preamble template of about six sections was copied, with drift, into four CLAUDE.md files in three different repos. Each copy picked up small local edits over time. In one of those repos, the root `CLAUDE.md` and its nested `.claude/CLAUDE.md` overlapped by about 90%. The nested file was a stale superset that nobody kept in sync with the edits of the root file. The right promotion candidate was the **reconciled** template: the drifted copies merged into one canonical version. It was not one copy, picked because it had the latest edit or looked the most complete. Classified **C-universal** for the reconciled result. Each of the four source copies (five with the stale nested superset) gets a `source:` citation in the same cluster.
