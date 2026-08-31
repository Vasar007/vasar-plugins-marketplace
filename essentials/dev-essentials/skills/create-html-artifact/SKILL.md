---
name: create-html-artifact
description: "Create a self-contained HTML artifact (implementation-plan view, PR/code review, comparison report, status dashboard, etc.) for the user to review in a browser instead of raw Markdown — inline CSS, mermaid diagrams, syntax-highlighted code snippets, mockups, and clickable findings/AC tables that deep-link to detail sections. Use whenever asked to render something as HTML, make a plan/review 'easy to read', produce mockups or a data-flow diagram, or save a visual report/artifact to a folder. Triggers: 'HTML artifact', 'html report', 'render as HTML', 'make this easier to review', 'mockups', 'data flow diagram', 'AC grid', 'visual plan', 'save an artifact'."
---

# Create HTML Artifact

Generic mechanics for turning structured content (a plan, a review, a report,
a status snapshot) into one self-contained, good-looking HTML file. This
skill owns the **document mechanics** — structure, CSS, diagrams, code
snippets, mockups. It does not own domain content: the calling task decides
what goes in each section.

**Not the same thing as this environment's built-in Artifact-publishing
tooling** (`artifact-design` / `artifact-diagramming` / the `Artifact` tool)
— that mechanism hosts a shareable web page on a platform-managed URL. This
skill instead writes a plain, self-contained `.html` file to disk in the
repo/task's own artifacts folder, for cases where the deliverable is a
repo-local file (an implementation-plan document, a PR-review report) rather
than a hosted, shareable page. Don't route this skill's output through the
`Artifact` tool, and don't use this skill when a hosted Artifact is what was
actually asked for.

If the artifact needs an actual chart/graph/KPI visualization (not just a
mermaid flow diagram), invoke the `dataviz` skill for the color/form rules,
then embed the result inside the structure below — `dataviz` is an optional
skill from elsewhere (not bundled with this plugin); if it isn't installed,
fall back to a plain, restrained chart styled consistently with the rest of
the artifact.

## Output conventions

- **One self-contained file** when possible: inline `<style>`, inline data.
  The only acceptable external references are CDN `<script src>` tags for
  mermaid (pinned to `mermaid@10.9.1`, matching the `mmdc` version used to
  verify diagrams offline) / highlight.js (pinned to
  `@highlightjs/cdn-assets@11`) — see gotchas below — no other network
  dependency, since the user opens this from disk.
- **Multi-file case**: if the content genuinely needs several linked HTML
  files (e.g. a main plan plus an appendix), keep each file
  self-contained on its own — duplicate the inline `<style>` block in
  every file rather than sharing an external stylesheet, since a file
  might be opened independently of the others. Use a consistent naming
  convention across the set (e.g. `<slug>-plan.html`,
  `<slug>-plan-appendix.html`) and link between them.
- **Reuse the most recent prior artifact in the same series as a visual
  template.** If this artifact is one of a recurring kind (weekly reports,
  PR reviews, plans for the same project), find the latest one already
  saved and copy its CSS variables, color scheme, and structural layout
  exactly, so the series stays visually consistent over time. Don't
  redesign from scratch each time. If no prior artifact in the series
  exists yet, start from the starter CSS in `references/css-components.md`
  instead.
- **Save location**: alongside the other artifacts for the task/PR/review
  this belongs to (e.g. the task's artifacts folder, a repo's
  `Notes/Reviews/`-style folder) — not in a scratch or temp location.
  Use a descriptive, greppable filename (`pr-<id>-review.html`,
  `<task-id>-implementation-plan.html`).
- Tell the user the artifact's path when done, as a final `ARTIFACT: <path>`
  line, so they can find it without re-asking — and so a calling
  skill/command can parse it back out programmatically. Any skill or
  command that invokes this one as a sub-step should look for that exact
  `ARTIFACT: <path>` line in the output rather than re-deriving the path.
  **Contract**: nothing else may follow `<path>` on that line — no trailing
  summary text, counts, or punctuation appended after the path. A caller
  that wants to report extra detail (a finding count, a one-line summary)
  puts it on its own separate line, before or after the `ARTIFACT:` line,
  never on the same line as the path. `<path>` itself may be either
  absolute or repo-relative — both conventions are in legitimate use by
  callers of this skill (e.g. an absolute path from a pipeline stage that
  already resolved `{WORKTREE_PATH}`, versus a repo-relative path like
  `Notes/Reviews/pr-<number>-review.html` from a review command run at the
  repo root); pick whichever fits the calling context, and stay consistent
  within that caller.

## Core structure — adapt sections to the content type

Not every artifact needs every section; pick what fits, keep the order:

1. **Header card** — title, a status/type pill, key metadata row (links,
   dates, authors, source → target, etc.).
2. **Stats grid** — 3–5 column glanceable numbers (counts, sizes, pass/fail
   totals). This is the "read in 5 seconds" row.
3. **Summary prose + highlight bullets** — plain-language description of
   what this artifact covers, plus a short bulleted list of the notable
   points (positives, risks, decisions).
4. **Legend** — only if you're using severity/status color coding anywhere
   below: colored dots/pills inline, one per category.
5. **Main table(s)** — findings / AC / steps, one row each, with a `#` and
   a deep-link (`<a href="#anchor-id">`) from each row down to its detail
   section. Every row that has more to say must be clickable.
6. **Collapsible detail groups** — `<details>` blocks grouping the above by
   file/area/stage, so the page stays scannable collapsed and detailed
   expanded.
7. **Annotated content sections** — the visual core, one of:
   - **Diff / annotated code**: 3-column CSS grid per line — line number |
     code | side annotation chip — with `id="anchor-id"` on the container
     so table rows can jump to it.
   - **Mockups**: plain HTML/CSS wireframe boxes (borders + labeled
     placeholder blocks). Don't chase pixel fidelity — just convey layout,
     hierarchy, and what's clickable.
   - **Mermaid diagrams**: data flow, sequence, or architecture diagrams.
     Read `references/mermaid-gotchas.md` before writing any mermaid block
     — most "syntax errors" reported later are not what they look like.
   - **Syntax-highlighted code snippets**: via highlight.js, browser CDN
     build only (see gotchas). Minimum recipe to get actual highlighted
     output, not just a correctly-pinned script tag: markup as
     `<pre><code class="language-<lang>">…</code></pre>` with the code text
     HTML-escaped (`<`, `>`, `&`) first; load
     `@highlightjs/cdn-assets@11/highlight.min.js` plus the specific
     `@highlightjs/cdn-assets@11/languages/<lang>.min.js` file(s) needed, then
     call `hljs.highlightAll();` once in a `<script>` after the DOM is ready;
     include a minimal theme by inlining the handful of `.hljs-*` color rules
     directly in the artifact's `<style>` block — a CDN `<link>` stylesheet
     is not an option here (see the "only acceptable external references"
     rule above, which permits `<script src>` only).
8. **Recommendation / next-steps** — 1–2 closing paragraphs: what matters
   now vs. what can wait.

For how these 8 sections map onto two common artifact types — an
implementation-plan view and a PR/code review — see
`references/recipes.md`. Use it as a starting template, not a rigid
requirement; adapt to the content at hand.

## Component patterns

- **Status/severity badges** — a consistent color map reused across the
  legend, table rows, and annotation chips. Common mapping (adapt labels to
  the domain — review severity, AC pass/fail, pipeline stage status):
  critical/blocked = red, major/warn = orange, minor = yellow, info = blue,
  good/pass = green, pending/n-a = gray.
- **Annotation chip** anchored to a specific line:
  `<span class="ann-card <severity>"><span class="tag"><severity> #N</span>…</span>`
- **AC grid** — table or CSS grid of acceptance criteria rows vs. status
  badge, each row linkable the same way findings rows are.
- Starter CSS for the grids/badges/collapsibles above lives in
  `references/css-components.md` — copy and adapt rather than
  reinventing the color math each time.

## Before you finish

- Every row in a summary table actually has a matching anchored detail
  section — dead deep-links are the most common defect in these artifacts.
- Any mermaid block has been sanity-checked per
  `references/mermaid-gotchas.md`.
- Grep the produced HTML for `highlight.js` / `<script src=...>`
  references and confirm they point at the `@highlightjs/cdn-assets@11`
  CDN pattern, not a `/lib/`-style npm path — that static check is what
  catches the `module is not defined` failure mode (see gotchas) without
  needing a browser. Do the same for the mermaid `<script src=...>` tag —
  confirm it is pinned to `mermaid@10.9.1`, not unpinned (`@mermaid/latest`
  or no version at all) and not some other version than the `mmdc` build
  used to verify diagrams offline (see `mermaid-gotchas.md`'s grep-gate
  list). Also grep the produced HTML for `<link` — any
  `<link rel="stylesheet" href="...">` pointing at an external URL is a
  defect (the "only acceptable external references" rule permits
  `<script src>` only, never a CDN stylesheet `<link>` — see the
  highlight.js recipe above). Full visual/console verification by actually
  opening the file is the user's job once they review it.
- Check `references/pitfalls.md` for the other recurring mistakes before
  calling this done.
- End the response with the `ARTIFACT: <path>` line described under
  "Output conventions" — nothing else on that line — this is the
  invocation contract any caller relies on to find the file.
