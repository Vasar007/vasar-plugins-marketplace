# Recurring pitfalls in HTML artifacts

Items here are additive to `SKILL.md` — see that file for the
self-contained-file, prior-artifact-reuse, live-anchor, and
render-verification rules. Only the genuinely distinct pitfalls are listed
below.

- **For long files/diffs, render representative excerpts, not everything**
  — but every table row's finding must still point at a rendered line via
  its annotation chip. Don't summarize a finding's location in prose only;
  the reader should be able to click straight to it.

- **Don't inflate content to look thorough.** A findings table padded with
  marginal nits reads as noise, not rigor — a healthy density for a
  ~1000-line review is roughly 1 major + a handful of minor/info items,
  not fifteen. The same principle applies to AC grids and step lists:
  report what's actually notable, not everything that could be said.

- **Ambiguous save location** — if it's genuinely unclear where in the
  repo/task-artifacts structure this artifact belongs (no existing
  series to match, no obvious folder), ask rather than guessing; getting
  this wrong means the user can't find the file later.
