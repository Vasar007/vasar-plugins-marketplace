# Recipes — mapping common artifact types onto the 8 generic sections

The core structure in `SKILL.md` defines 8 generic sections. This file maps the domain content of two recurring artifact types onto those sections. A caller then does not have to work out the mapping each time. Both recipes are patterns, not templates to copy word for word. Adapt the field names to the data that the calling task has.

## Recipe 1 — Implementation-plan artifact

Use this recipe to render an approved implementation plan as an HTML artifact for review. The plan has a spec, the steps in execution order, and acceptance criteria (AC). A plan-then-implement workflow usually makes this artifact before a human-approval gate.

1. **Header card**: the title of the task or the spec, and the current stage or status, for example "awaiting approval" or "in progress". Add a link back to the tracker item of the task (an issue or a ticket).
2. **Stats grid**: the count of steps in the execution order, the count of changed files, and the counts of AC that pass and fail.
3. **Summary**: a plain-language description of what the task builds, from the overview section of the spec.
4. **Legend**: the color code for AC and step statuses, for example planned, in progress, and done. If no section below uses status badges, leave the legend out.
5. **Main table(s)**: the AC grid and the list of execution-order steps, with one row for each AC or step. Each row has a deep link (`<a href="#anchor-id">`) down to its detail section.
6. **Collapsible detail groups**: one `<details>` block for each file or each execution-order step. The blocks group the detailed content, so that the page stays easy to scan with the blocks closed.
7. **Annotated content**: the mermaid data-flow or architecture diagram, mockups of the resulting UI, and the code snippets that the reviewer needs to see before the approval.
8. **Recommendation**: the open questions and the risks that the human needs to know before the approval of the plan.

## Recipe 2 — PR / code-review artifact

Use this recipe to render a finished code review (findings against a diff) as an HTML artifact for review. Such an artifact is usually saved next to the other review artifacts of the same repository or PR series.

1. **Header card**: the PR title, a status pill (for example Active or Completed), a link back to the PR, and the author. Add a row with the source branch, the target branch, and their tip commits.
2. **Stats grid**: the changed files, the added and removed lines, the commits on the branch, and the finding counts by severity in one cell.
3. **Summary paragraph and positive bullets**: what the change does, in plain prose. Add a short bulleted list of the conventions and patterns that it follows well.
4. **Severity legend**: colored dots, inline: critical (red), major (orange), minor (yellow), info (blue), and good (green).
5. **Findings table**: the `#`, a severity badge, a "Where" cell, and the description of the finding. The "Where" cell has a deep link (`<a href="#F-<anchor>">`) to the detail section of the file. Every finding must have a link.
6. **"Major changes by file"**: collapsible `<details>` sections, usually one for production code and one for tests. Each one lists the files with their line counts, and links back to the findings that touch each file.
7. **Annotated diff sections**: one section for each file. Use the annotated line grid from `references/css-components.md`: the line number, the code, and a side annotation chip in the severity color. Give each file section the anchor `id="F-<anchor>"` that the deep links of the findings table use. Render the real diff, with added lines in green, removed lines in red, and context lines in gray. For a very long file, render excerpts, but each finding must still point to its line with a chip.
8. **Recommendation**: what the author must fix before the merge, and what can wait for a follow-up.

## Notes for both recipes

Keep the counts of findings and AC honest (see `references/pitfalls.md`). A table with padding to look thorough is a known anti-pattern.
