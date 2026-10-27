# Report templates

Phase 4 of `SKILL.md` reads this file. Copy the template, replace the bracketed placeholders, and fill every table. Do not change the section structure of the template.

## Phase 4 triage template

The "0. Disposition legend" table repeats the six-value enum of Phase 3 in `SKILL.md`. With it, the reader of the triage does not need `references/classification-framework.md` to decode a letter. If the enum changes, change the legend too.

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
