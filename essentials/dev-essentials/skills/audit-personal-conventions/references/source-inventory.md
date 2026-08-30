# Source Inventory — Structural Landmines

Referenced by Phase 1 of `SKILL.md`. Discovery paths and the encoded-project-name
decode/probe/worktree-collapse procedure live inline in `SKILL.md`'s Phase 1 section, since they
apply on every run; this file holds the twelve structural landmines, which only matter once files
are actually being read, and only for the source types in scope.

All paths below are expressed relative to `<claude-root>`, resolved per the path resolution rule in
`SKILL.md` (`CLAUDE_CONFIG_DIR` env var if set, else `<home>/.claude`). Never hardcode a concrete
path in output — always show paths relative to `<claude-root>` or the relevant repo root.

---

## The twelve structural landmines

Read this list before extracting rules in Phase 2 — each landmine causes a specific, real misread
if skipped.

1. **Frontmatter shape variance.** Some memory files nest metadata under a `metadata:` block with a
   `metadata.type` field; others use a flat top-level `type:` field; others have no frontmatter at
   all. Do not assume a shape — check each file.
2. **Unquoted `#` truncating YAML.** A `description:` value containing an unquoted `#` character is
   silently truncated by the YAML parser at that character (`#` starts a YAML comment). A rule
   whose description reads "handles retries # see also X" will parse as "handles retries" only.
   Read the raw file content, not just a parsed frontmatter object, when a description looks
   suspiciously short.
3. **Missing `Why:`/`How to apply:` sections.** Do not assume every memory file follows the
   Why/How-to-apply shape — a majority of real files skip one or both. Extract the rule from
   whatever prose is actually present.
4. **Wikilink hazards.** Memory files sometimes use `[[Page]]`-style links.
   - Filename/link-slug convention mismatches exist within a single project — a link may not
     resolve even though the target file exists, because the slugging rule differs from the actual
     filename.
   - Some links point AT a skill name intentionally (a forward reference to "this should become
     `plugin:skill-name`") — these are not dangling, they are provenance breadcrumbs.
   - Some links are genuinely dangling (the target was deleted or renamed and the link was never
     updated).
   - Link scope is per-project — a link that resolves in one project's memory directory will not
     resolve when read from a different project; do not treat a cross-project dangling link as
     evidence the content is stale.
   - MediaWiki-style `[[Page]]` / `[[Category:...]]` syntax sometimes appears as **literal example
     content** inside a fenced or inline code span (e.g. documenting how to write a wiki page).
     Exclude matches inside fenced code blocks, inline code spans, and any `Category:`-prefixed
     match from wikilink-hazard analysis — those are not real links.
5. **Same-slug files diverged across two projects.** Two projects can independently accumulate a
   memory file with the same filename/slug that has drifted apart in content. Merge and reconcile
   the two into one candidate rule set — never arbitrarily pick one project's version and discard
   the other's additions.
6. **Dated append-blocks.** Some memory files grow by appending `## Update (YYYY-MM-DD)` blocks over
   time, where a later block supersedes an earlier statement on the same topic without removing the
   earlier text. Read the whole file and take the latest position on any given point, not the first
   occurrence.
7. **Stale `MEMORY.md` index entries.** A project's `MEMORY.md` index can reference a memory file
   that has since been deleted or renamed. The index is not ground truth — verify every referenced
   file actually exists on disk before trusting an index entry's claim (including its own
   "migrated" claims, per Phase 3).
8. **CLAUDE.md `@`-imports.** A CLAUDE.md file can `@`-import another file's content. Resolve the
   import chain and treat imported content as belonging to the importing file's scope for
   inheritance purposes, while still citing the imported file's own path in the `source:` field.
9. **Near-duplicate CLAUDE.md pairs with content drift.** A repo root `CLAUDE.md` and a nested
   `.claude/CLAUDE.md` (or a deeper subdirectory `CLAUDE.md`) can overlap heavily — sometimes with
   the deeper file being a STALE superset that was copied once and never kept in sync. Dedupe by
   content, not by location: read both in full and reconcile, do not assume the deeper file is
   automatically more specific or more current.
10. **Nested-file inheritance/scope-negation statements.** A nested CLAUDE.md sometimes explicitly
    narrows or negates a parent-scope rule ("unlike the repo default, this subfolder does NOT use
    X"). Honor these explicitly when extracting rules in Phase 2 — a flattening scan that ignores
    nesting will mis-scope the rule onto the wrong folder, or worse, silently drop the negation and
    treat the parent rule as unconditionally universal.
11. **Vendored/third-party CLAUDE.md files.** A personal repo can contain a vendored or third-party
    dependency that ships its own `CLAUDE.md`. Exclude these by default — they document someone
    else's project conventions, not the user's own. `--include-vendored` overrides this exclusion
    (clearly labelled as vendored in the inventory output when included).
12. **Wrapper personal entities.** A personal command, agent, or skill wrapping a shipped entity must
    be diffed against the entity it wraps — never read in isolation. Detect a wrapper by either of
    these two signals (either alone is sufficient to trigger the diff) — trimmed to the two shapes
    that actually occur in practice, a forwarding wrapper and a name/description-declared wrapper:
    - (i) the body contains a `$ARGUMENTS`-forwarding line anywhere in the file, not only as the
      first line;
    - (ii) the filename or frontmatter `description` explicitly names, wraps, extends, or refines a
      shipped entity.

    A wrapper shaped some other way is caught by ordinary human judgment during the Phase 1 read,
    not by a longer enumerated list.

    Reading the wrapper alone either re-promotes content that is already upstream in the wrapped
    entity, or misses that the wrapper's real "delta" is actually a bug report against the base
    entity (see `references/classification-framework.md` disposition **E**, and
    `examples/fix-shipped-entity.md` case 2 for a worked instance of exactly this landmine). Wrapper
    diffing is not exclusive with the wrapper legitimately staying personal — see
    `references/classification-framework.md` Step 4's orthogonality rule: a wrapper found intentional
    can still carry individually-diffed divergences worth their own disposition.

---

## Read-only guarantee

No file discovered in Phase 1 is modified, moved, or deleted there under any flag combination —
writes happen only in Phase 6 (new entities in the target marketplace), Phase 9 (source-side
cleanup, each sub-phase independently gated), and Phase 10's optional report file.
