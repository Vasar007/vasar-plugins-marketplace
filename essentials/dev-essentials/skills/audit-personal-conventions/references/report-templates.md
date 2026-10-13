# Report templates

Phase 4 and Phase 10 of `SKILL.md` read this file. Copy each template, replace the bracketed placeholders, and fill every table. Do not change the section structure of the Phase 4 template. The Phase 10 report also holds the items that "Autonomy" in `SKILL.md` asks for.

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

## Phase 10 run report template

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
