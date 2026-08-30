# Recipes — mapping common artifact types onto the 8 generic sections

`SKILL.md`'s core structure defines 8 generic sections. This file works out,
for two recurring artifact types, which domain content lands in which
section — so a caller doesn't have to re-derive the mapping from scratch
each time. Both recipes below are patterns, not templates to copy verbatim:
adapt field names to whatever the calling task actually has on hand.

## Recipe 1 — Implementation-plan artifact

For rendering an approved implementation plan (spec, execution-order steps,
and acceptance criteria) as a reviewable HTML artifact, typically produced
before a human-approval gate in a plan-then-implement workflow.

1. **Header card** — the task/spec title, the current stage or status
   (e.g. "awaiting approval", "in progress"), and a link back to the
   task's tracker item (work item, ticket, issue).
2. **Stats grid** — execution-order step count, files touched, AC
   pass/fail counts.
3. **Summary** — a plain-language description of what's being built,
   pulled from the spec's overview section.
4. **Legend** — AC/step status color coding, if the plan uses status
   badges anywhere below (e.g. planned / in-progress / done).
5. **Main table(s)** — the AC grid plus the execution-order step list, one
   row per AC / step, each deep-linking (`<a href="#anchor-id">`) down to
   its detail section.
6. **Collapsible detail groups** — one `<details>` per file or per
   execution-order step, grouping the finer-grained content so the page
   stays scannable collapsed.
7. **Annotated content** — the mermaid data-flow (or architecture)
   diagram, any mockups of the resulting UI, and the important code
   snippets worth reviewing before approval.
8. **Recommendation** — open questions or risks worth flagging before the
   human approves the plan.

## Recipe 2 — PR / code-review artifact

For rendering a completed code review (findings against a diff) as a
reviewable HTML artifact, typically saved alongside other review artifacts
for the same repo/PR series.

1. **Header card** — PR title, status pill (e.g. Active / Completed),
   link back to the PR, author, and the source-branch → target-branch row
   with commit tips.
2. **Stats grid** — files changed; lines added / removed; commits on the
   branch; finding counts by severity in one cell.
3. **Summary paragraph + positive bullets** — what the change does in
   plain prose, plus a short bulleted list of the conventions/patterns it
   follows well.
4. **Severity legend** — colored dots inline: critical (red), major
   (orange), minor (yellow), info (blue), good (green).
5. **Findings table** — `#`, severity badge, a "Where" cell deep-linking
   (`<a href="#F-<anchor>">`) to the file's detail section, and the
   finding description. Every finding must be linkable.
6. **"Major changes by file"** collapsible `<details>` sections — typically
   one for production code and one for tests — each listing files with
   line counts and back-references to the findings that touch them.
7. **Annotated diff sections** — one section per file, using the
   annotated-line-grid pattern from `references/css-components.md` (line
   number | code | side annotation chip, color-coded by severity). Anchor
   each file section with `id="F-<anchor>"` tied to the findings table's
   deep-links. Render the actual diff (added lines in green, removed in
   red, context in gray); for very long files, render representative
   excerpts but every finding must still point to its line via a chip.
8. **Recommendation** — what's must-fix before merge vs. what can be a
   follow-up.

## Notes for both recipes

+ Don't force every section to be present if the content genuinely has
  nothing for it (e.g. skip the legend if nothing below uses color
  coding) — see `SKILL.md`'s "adapt sections to the content type" note.
+ Keep finding/AC density honest per `references/pitfalls.md` — padding
  either table to look thorough is a known anti-pattern.
+ If this artifact is part of a recurring series (weekly plan renders,
  repeated PR reviews for the same repo), reuse the most recent prior
  artifact's CSS and layout rather than restyling from these recipes each
  time — see `SKILL.md`'s "reuse the most recent prior artifact" rule.
