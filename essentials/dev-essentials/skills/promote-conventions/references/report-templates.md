# Report templates

Phase 10 of `SKILL.md` reads this file. Copy the template, replace the bracketed placeholders, and fill every table. The Phase 10 report also holds the items that "Autonomy" in `SKILL.md` asks for.

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

F<n> [<verdict>] — <finding and fix>
source: <path>:<line>

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

## Gates passed without a stop

| Gate | Default taken | Saved to |
|---|---|---|

## Actions taken in the full mode

- <deletion / push / PR / post>, or "none"

## Decisions for your review

- <decision and why>, or "none"

## Commits

<sha> <subject>   (local only — nothing pushed unless a Phase 9c push-gate said yes)
```
