---
name: create-html-artifact
description: "Create a self-contained HTML file that the user reviews in a browser instead of raw Markdown. Examples are a plan view, a PR review, a comparison report, or a status dashboard. It uses inline CSS, diagrams, highlighted code, and mockups."
when_to_use: "Use it for 'HTML artifact', 'html report', 'render as HTML', 'make this easier to review', or 'mockups'. Do not use it for a hosted Artifact page."
---

# Create HTML Artifact

This skill turns structured content into one self-contained HTML file. Examples of such content are a plan, a review, a report, and a status snapshot. The skill owns the document mechanics: structure, CSS, diagrams, code snippets, and mockups. The calling task owns the domain content and decides what goes into each section.

This skill is not the built-in Artifact publishing of the environment (`artifact-design`, `artifact-diagramming`, and the `Artifact` tool). That tool hosts a shareable web page at a URL that the platform manages. This skill writes a plain `.html` file to disk, into the artifacts folder of the repository or of the task. If the deliverable is a file in the repository, for example an implementation-plan document or a PR-review report, use this skill. Do not send the output of this skill through the `Artifact` tool. If the user asked for a hosted Artifact, do not use this skill.

If the artifact needs a chart, a graph, or a KPI visualization, invoke the `dataviz` skill for the color and form rules. A mermaid flow diagram does not need it. Put the result of `dataviz` into the structure below. `dataviz` is an optional skill from outside this plugin. If it is not installed, draw a plain, restrained chart in the style of the rest of the artifact.

## Output conventions

- **One self-contained file** where possible, with an inline `<style>` block and inline data. The user opens the file from disk, so the file has no network dependency except these CDN `<script src>` tags (see `references/mermaid-gotchas.md`):
  - mermaid, pinned to `mermaid@10.9.1`. This is the version of the `mmdc` tool that tests the diagrams offline.
  - highlight.js, pinned to `@highlightjs/cdn-assets@11`.
- **Multi-file case**: if the content needs several linked HTML files, for example a main plan and an appendix, keep each file self-contained. Copy the inline `<style>` block into each file, and do not share an external stylesheet, because the user can open one file without the others. Use one naming pattern for the set, for example `<slug>-plan.html` and `<slug>-plan-appendix.html`. Link the files to each other.
- **Reuse the most recent prior artifact in the same series as a visual template**. A series is a recurring kind of artifact, for example weekly reports, PR reviews, or plans for one project. Find the latest saved artifact of the series. Copy its CSS variables, color scheme, and layout exactly, so that the series looks the same over time. Do not redesign from scratch each time. If the series has no artifact yet, start from the starter CSS in `references/css-components.md`.
- **Save location**: save the file next to the other artifacts of its task, PR, or review. Examples are the artifacts folder of the task, or a folder like `Notes/Reviews/` in the repository. Do not save it in a scratch or temp folder. Use a descriptive file name that grep can find, for example `pr-<id>-review.html` or `<task-id>-implementation-plan.html`.
- **The `ARTIFACT: <path>` line**: after you write the file, put its path into your final output as one `ARTIFACT: <path>` line. The user then finds the file without a question. A skill or command that calls this skill must read the path from this exact line, and must not work out the path again.
  - Contract: put nothing after `<path>` on that line. Add no summary text, no counts, and no punctuation.
  - A caller that reports more detail, for example a finding count or a one-line summary, puts it on a separate line. That line can come before or after the `ARTIFACT:` line.
  - `<path>` can be absolute or relative to the repository root. Use the form that fits the caller, and use it the same way in each run of that caller. Example: a pipeline stage that resolved `{WORKTREE_PATH}` gives an absolute path. A review command that runs at the repository root gives `Notes/Reviews/pr-<number>-review.html`.

## Core structure — adapt sections to the content type

Not every artifact needs every section. Pick the sections that fit, and keep this order:

1. **Header card**: the title, a status or type pill, and a row of key metadata, for example links, dates, authors, or source and target.
2. **Stats grid**: 3 to 5 columns of numbers that the reader takes in at a glance, for example counts, sizes, or pass and fail totals. This is the row that the reader reads in 5 seconds.
3. **Summary prose and highlight bullets**: a plain-language description of what the artifact covers. Add a short bulleted list of the notable points, for example positives, risks, and decisions.
4. **Legend**: if a section below uses severity or status colors, show one colored dot or pill for each category, inline. Else leave the legend out.
5. **Main table(s)**: findings, acceptance criteria (AC), or steps, with one row each. Each row has a `#` and a deep link (`<a href="#anchor-id">`) down to its detail section. Every row with more detail must be clickable.
6. **Collapsible detail groups**: `<details>` blocks that group the rows above by file, area, or stage. Closed groups keep the page easy to scan. Open groups show the details.
7. **Annotated content sections**: the visual core. Use one of these:
   - **Diff or annotated code**: a 3-column CSS grid for each line, with the line number, the code, and a side annotation chip. Put `id="anchor-id"` on the container, so that table rows can jump to it.
   - **Mockups**: plain HTML and CSS wireframe boxes, with borders and labeled placeholder blocks. Do not aim for pixel accuracy. Show the layout, the hierarchy, and the parts that the user can click.
   - **Mermaid diagrams**: data flow, sequence, or architecture diagrams. Read `references/mermaid-gotchas.md` before you write a mermaid block. Most "syntax errors" that mermaid reports later have a different cause.
   - **Syntax-highlighted code snippets**: use highlight.js, the browser CDN build only (see `references/mermaid-gotchas.md`). A correctly pinned script tag alone does not highlight the code. Do all of these steps:
     1. Mark up each snippet as `<pre><code class="language-<lang>">…</code></pre>`. HTML-escape the code text first (`<`, `>`, `&`).
     2. Load `@highlightjs/cdn-assets@11/highlight.min.js` and each `@highlightjs/cdn-assets@11/languages/<lang>.min.js` file that you need.
     3. Call `hljs.highlightAll();` once, in a `<script>` that runs after the DOM is ready.
     4. Copy a small theme into the `<style>` block of the artifact: the few `.hljs-*` color rules. Do not load a CDN `<link>` stylesheet. The rule on external references in "Output conventions" allows `<script src>` tags only.
8. **Recommendation or next steps**: one or two closing paragraphs. Say what matters now and what can wait.

`references/recipes.md` maps these 8 sections onto two common artifact types: an implementation-plan view and a PR or code review. Use it as a starting template, not as a fixed rule. Adapt it to the content.

## Component patterns

- **Status and severity badges**: use one color map for the legend, the table rows, and the annotation chips. Adapt the labels to the domain, for example review severity, AC pass or fail, or pipeline stage status. A common map:
  - critical or blocked: red
  - major or warn: orange
  - minor: yellow
  - info: blue
  - good or pass: green
  - pending or n/a: gray
- **Annotation chip** on a specific line: `<span class="ann-card <severity>"><span class="tag"><severity> #N</span>…</span>`
- **AC grid**: a table or a CSS grid of AC rows, each with a status badge. Link each row in the same way as a findings row.
- `references/css-components.md` has starter CSS for the grids, badges, and collapsible groups above. Copy it and adapt it, so that you do not work out the color math again each time.

## Before you finish

- Every row of a summary table has a matching anchored detail section. A dead deep link is the most common defect in these artifacts.
- Each mermaid block passes the grep counts of item 1 of "Required verification artifacts" in `references/mermaid-gotchas.md`. Items 2 and 3 of that list (the `mmdc` test and the test page) are for a fix pass, after a diagram does not render.
- Grep the HTML for `highlight.js` and `<script src=...>` references. Make sure that they use the CDN pattern `@highlightjs/cdn-assets@11`, not an npm path with `/lib/`. This static test finds the `module is not defined` failure (see `references/mermaid-gotchas.md`) without a browser.
- Do the same for the mermaid `<script src=...>` tag. Make sure that it is pinned to `mermaid@10.9.1`. A tag with no version or with `@mermaid/latest` is a defect. A tag with another version than the `mmdc` build that tests the diagrams offline is also a defect (see the grep list in `references/mermaid-gotchas.md`).
- Grep the HTML for `<link`. A `<link rel="stylesheet" href="...">` to an external URL is a defect. The rule on external references in "Output conventions" allows `<script src>` tags only, and never a CDN stylesheet (see the highlight.js steps above).
- Read `references/pitfalls.md` for the other common mistakes before you call the work done.
- Put the `ARTIFACT: <path>` line of "Output conventions" into your final output, with nothing else on that line. Every caller depends on this line to find the file.

The full visual and console test is the job of the user, who opens the file to review it.
