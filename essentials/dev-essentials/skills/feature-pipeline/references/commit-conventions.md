# Commit conventions

The master agent reads this file at Step 0 of `SKILL.md`, and again before it composes the prompt of a commit-capable stage. It holds the `<commit-conventions>` block. This block is the only source of the commit-message rules of the pipeline.

## Injection rules

- Five stages get the block: `implementation`, `test-coverage`, `simplifier`, `docs`, and `finalization`. No other stage gets it.
- Copy the fenced block below **verbatim**. Do not paraphrase, summarize, reorder, or trim its bullets.
- Exactly two things change on the way in. The `{CADENCE_LINE}` token becomes the line for the resolved `{COMMIT_MODE}` (see "Cadence lines"). `{ARTIFACTS_DIR}` is replaced like every other placeholder.
- Prepare the block once, after Step 0 resolves `{COMMIT_MODE}` and before the first stage launch. In one run, the block is the same for each stage that gets it.
- If the block in a composed prompt differs from the source in any other way, the prompt has a defect. The stage subagents never see `SKILL.md`, so a paraphrase silently becomes the rule.

## Cadence lines

`{CADENCE_LINE}` is resolved from this list, not by a placeholder replacement. It never reaches a stage prompt as a token. Use exactly one line.

For `{COMMIT_MODE}` = `finalization`:

```text
Commit cadence for this run: **finalization**. Only the Finalization stage creates a commit — one commit for the whole run. Every earlier stage stages its own changes with an explicit `git add <path>` (never `-A` or `.`) and does NOT commit.
```

For `{COMMIT_MODE}` = `per-step`:

```text
Commit cadence for this run: **per-step**. Each stage commits its own changes as they go green, staging with an explicit `git add <path>` (never `-A` or `.`). The Finalization stage creates no commit — it expects a clean tree. Your stage's commit granularity is defined in your own stage instructions.
```

## Block body

Inject this block verbatim:

```md
{CADENCE_LINE}

Commit-message rules — these apply to EVERY commit you create in this run.
Follow them exactly; do not invent your own format.

- **Subject** — ≤70 chars, describing WHAT changed, not HOW. Match the repo's
  existing commit-subject convention: infer it by running `git log --oneline`
  against the base branch named in the Project Context above.
- **Body** — optional; 1-2 lines on WHY, in production-engineering terms. If
  the repo's history shows no multi-line commit bodies, omit the body.
- **No pipeline-internal references** anywhere in the message: no
  `{ARTIFACTS_DIR}/...` paths, no artifact section anchors (e.g. `spec.md §4`),
  no review-finding IDs, no pipeline stage names. Per
  `dev-essentials:engineering-discipline` Rule 3, the message must read
  as production engineering history that still resolves six months from now.
- **Trailer** — end the message with the standard Claude `Co-Authored-By`
  trailer. Do NOT hardcode a model name or version — use the exact trailer
  string the harness gives you for the model actually making this commit.
- **NEVER `--no-verify`.** If a hook fails, fix the underlying issue.
- **NEVER amend.** If anything needs correcting after a commit exists, create
  a NEW commit.
- **Commit with paths.** Run `git commit -m <message> -- <path> ...`, with the
  paths that you staged. A change that the user staged before the run then
  stays staged and out of the commit. For a rename or a delete, put the old
  path and the new path after `--`. To find the old path of a rename, run
  `git diff --cached --name-only --no-renames`. This command lists every
  staged path, also a path that the user staged before the run. Commit only
  your own paths from that list.
- **NEVER `git add -f`.** If git says that a path is ignored, leave it out, and
  name it in your final reply. A `.gitignore` entry often keeps local secrets
  out of the repository.
- **Do not push from your stage**. The master agent pushes after the
  Finalization stage. This holds for the Finalization stage too.
- **Never commit anything under `{ARTIFACTS_DIR}/`.**
```
