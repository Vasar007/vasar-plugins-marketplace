# Entity Authoring Conventions — Phase 6

Referenced by Phase 6 of `SKILL.md`. Distilled from an earlier ad-hoc promotion in this marketplace's
history — see SKILL.md's opening preamble for the full precedent.

---

## Skill vs. command vs. agent selection

Three shapes, three different growth profiles. Pick based on which shape the approved rule(s)
actually need — not habit, and not "skills are more flexible so default to skill".

- **Command** — a one-shot, single-file, user-typed procedure with no growth path. The user types
  `/plugin:name`, the procedure runs once, end of story. Right shape when the content is a fixed
  linear script with no branching phases and no reference-file depth.
- **Skill** — model-invoked (triggers from a description match, not only from being typed), needs
  triggering plus progressive disclosure, and often needs multi-file depth (`references/`,
  `examples/`). Right shape when the content has phases, flags, decision trees, or grows over time.
- **Agent** — a persona pinned to a restricted tool allowlist. Right shape when the content is best
  expressed as "a specialized worker with only these tools", not as instructions the main session
  follows itself.

**Concrete precedent:** this marketplace's own history deleted the commands `/review-loop` and
`/review-pr` in favor of the single skill `dev-essentials:review-loop`, precisely because those
commands had outgrown the one-shot linear-script shape — they had accumulated phases, flags, and
reference-file-worthy depth that a command's single-file, no-growth-path shape could not hold
cleanly. That deletion is
also the concrete example of a MAJOR-bump-triggering change (see "Version bump" below): removing an
existing invocation path (`/review-loop`, `/review-pr`) is exactly the MAJOR case.

## Frontmatter — this skill's own template sticks to `name` and `description`

Claude Code's skill frontmatter schema supports several optional fields beyond `name` and
`description` — `allowed-tools`, `model`, `context`, `disable-model-invocation`, `argument-hint`, and
others (see the current official Claude Code skill-frontmatter documentation for the full list); this
marketplace's own `dev-essentials:feature-pipeline` skill ships `argument-hint` and
`disable-model-invocation` today. Do not claim a skill's frontmatter is restricted to two fields, or
that adding an optional field is a schema error — it is not.

**By convention, the entity this skill authors in Phase 6 sticks to `name` and `description` only**,
because the rules promoted through this skill are description-triggered procedures, not
manually-invoked or tool-restricted ones. Add an optional field only when the authored entity
actually needs that specific behavior (e.g. `disable-model-invocation: true` for a workflow with side
effects) — not by default.

**`name` must equal the directory name, exactly.** A real mismatch (a skill's frontmatter `name`
differing from its containing directory name) was found and fixed as a bug during this
marketplace's own history — treat this as a hard invariant to check on every authored or edited
skill, not an edge case.

## The 3-part description recipe

A skill's `description` field is the only signal the runtime uses to decide whether to trigger the
skill. Write it in three parts:

1. **What it covers and when to use it** — a plain-language statement of the skill's job.
2. **Explicit coverage enumeration** — the specific sub-topics, flags, or scenarios it handles,
   named individually rather than left implicit.
3. **A "Triggers on requests like..." clause** — several concrete phrasings a user might actually
   type, in quotes, so the runtime's matching has literal strings to anchor on.

**Made-up example**, illustrating the shape (not a real skill in this marketplace):

> "Manage feature-flag rollout stages for a .NET service — covers creating a new flag, promoting a
> flag from canary to full rollout, and retiring a flag once fully rolled out. Handles the
> environment-config file update, the flag-owner changelog entry, and the Slack notification that
> accompanies a promotion. Triggers on requests like 'add a feature flag', 'promote this flag to
> 100%', 'retire the flag for X', or 'roll back this flag'."

## Body structure

- **H1 title** matching the skill's name in prose form.
- **Provenance preamble**, literally in the style: "This skill consolidates `<N>` rules the user has
  corrected the main agent on enough times that they belong here, not just in personal memory" (or
  the equivalent framing for a skill mined from a different kind of precedent, as this very skill's
  own preamble does for the earlier ad-hoc promotion it was mined from).
- **`## Rule N — <imperative>`** sections, each containing:
  - **Why** — the reasoning or failure mode that makes the rule necessary.
  - **How to apply** — the concrete mechanics.
  - **Anti-patterns** — named wrong approaches the rule exists to prevent.
- **Closing cross-references** — a table naming related skills/entities and why this one depends on
  or complements each.

## References vs. examples — conditional need, not line count

Split content into `references/*.md` or `examples/*.md` only when a chunk of content applies
conditionally — to only one of several invocation branches, target types, or flag combinations —
not because the main `SKILL.md` file crossed some line-count threshold.

Two data points from this marketplace, in opposite directions:

- Single-file skills with no subfolder at all run as long as roughly 500+ lines when every part of
  the content applies unconditionally to every invocation.
- A skill as short as roughly 150 lines can still justify a `references/` split, when a meaningful
  chunk of that content only applies to one of several branches (e.g. one target type out of eight,
  one disposition out of six) and would otherwise force every reader to scroll past content that
  doesn't apply to their case.

## Author-commit-pairing discipline

Ship an authored or edited entity as at least two commits:

1. An **"Add X"** (or "Edit X") commit with the entity's initial content.
2. An **"Apply review findings"** commit, once a review pass has run (Phase 7), whose body cites
   numbered findings `F1`/`F2`/`F3`/... — each finding traced to a `source: <file>:<line>` citation.

This is the same `source:` citation format Phase 2 uses for rule extraction — cite it for your own
review/verification purposes during this session, so the fixer and reviewer can trace a generalized
rule back to the exact file and line it came from while the run is live. Do not present this as a
stable, permanent commit-message convention: the cited file commonly lives under the user's own
personal, non-repo `<claude-root>` config (a memory file, a global CLAUDE.md), which sits outside the
marketplace repo entirely and is not resolvable by a future reader of just the shipped repo's git
history.

## Version bump

Bump rules, severities, and the mid-run-double-bump precedent are specified in `SKILL.md`'s Phase 8
— nothing here overrides them. The one addition from the precedent above: the `/review-loop` +
`/review-pr` → `review-loop` consolidation is the concrete MAJOR case (an existing invocation
path removed).

## Extend vs. create

Re-apply `references/classification-framework.md`'s Step 7 gap-vs-overlap check here, in Phase 6,
before authoring a brand-new entity — Step 7 runs before Phase 4 proposes a destination, but Phase 6
is where the actual skill/command/agent selection acts on the answer. In short: a **gap** means no
existing entity covers this, so a new entity is justified; an **overlap** means an existing entity
already covers this territory, even if incompletely, so extend that entity (an additional
`## Rule N` section, an additional reference file) instead of authoring a near-duplicate that will
drift from the original over time. See Step 7 in `classification-framework.md` for the full check.
