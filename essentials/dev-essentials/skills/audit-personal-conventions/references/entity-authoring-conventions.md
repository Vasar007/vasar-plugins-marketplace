# Entity Authoring Conventions — Phase 6

Phase 6 of `SKILL.md` reads this file. The conventions come from an earlier ad-hoc promotion in the history of this marketplace (see the intro of `SKILL.md`).

---

## Skill vs. command vs. agent selection

The three shapes grow in different ways. Pick the shape that the approved rules really need. Do not pick by habit, and do not default to a skill because "skills are more flexible".

- **Command**: a one-shot, single-file procedure that the user types, with no growth path. The user types `/plugin:name`, and the procedure runs once. Use a command for a fixed linear script with no branching phases and no reference-file depth.
- **Skill**: model-invoked. It triggers from a description match, not only from a typed command. It needs triggering and progressive disclosure, and it often needs multi-file depth (`references/`, `examples/`). Use a skill for content with phases, flags, or decision trees, or for content that grows over time.
- **Agent**: a persona with a restricted tool allowlist. Use an agent for content that works best as "a specialized worker with only these tools", not as instructions that the main session follows itself.

**Concrete precedent**. The history of this marketplace deleted the commands `/review-loop` and `/review-pr` in favor of the single skill `dev-essentials:review-loop`. Those commands outgrew the one-shot linear-script shape. They had phases, flags, and enough depth for reference files, which a single-file command cannot hold cleanly. The deletion is also the concrete MAJOR case of a version bump, because it removed existing invocation paths (`/review-loop`, `/review-pr`).

## Frontmatter — this skill's own template sticks to `name` and `description`

The Claude Code skill frontmatter supports several optional fields beyond `name` and `description`. Examples are `allowed-tools`, `model`, `context`, `disable-model-invocation`, and `argument-hint`. The official Claude Code skills documentation has the full list. `dev-essentials:feature-pipeline` sets `argument-hint` and `disable-model-invocation`. Do not claim that skill frontmatter allows only two fields, or that an optional field is a schema error. It is not.

**By convention, the entity that this skill authors in Phase 6 uses only `name` and `description`**. The rules that this skill promotes are description-triggered procedures. They are not procedures that the user invokes by hand or that need restricted tools. If the authored entity needs the specific behavior of an optional field, add that field, for example `disable-model-invocation: true` for a workflow with side effects. Never add an optional field by default.

**`name` must equal the directory name, exactly**. The history of this marketplace had a real bug: the frontmatter `name` of a skill differed from the name of its directory. Make sure that each authored or edited skill keeps this invariant. It is a hard rule, not an edge case.

## The 3-part description recipe

Claude reads the `description` of a skill to decide whether to use the skill. Write it in three parts:

1. **What it covers and its use cases**: a plain statement of the job of the skill.
2. **Explicit coverage enumeration**: the specific sub-topics, flags, or scenarios that it handles, each one named, not left implicit.
3. **A "Triggers on requests like..." clause**: several concrete phrases in quotes that a user can type. They give Claude literal strings to match.

**Made-up example** of the shape (not a real skill in this marketplace):

> "Manage the rollout stages of feature flags for a web service. Covers how to create a new flag, promote a flag from canary to full rollout, and retire a flag after full rollout. Handles the update of the environment configuration file, the changelog entry of the flag owner, and the Slack notification that goes with a promotion. Triggers on requests like 'add a feature flag', 'promote this flag to 100%', 'retire the flag for X', or 'roll back this flag'."

## Body structure

- **H1 title**: the name of the skill in prose form.
- **Provenance preamble**, in this style: "This skill consolidates `<N>` rules that the user corrected the main agent on many times. They belong here, not only in personal memory." A skill that comes from another kind of precedent uses an equivalent frame. The intro of this skill is an example: it names the earlier ad-hoc promotion that the skill comes from.
- **`## Rule N — <imperative>`** sections. Each one has:
  - **Why**: the reasoning or the failure mode that makes the rule necessary.
  - **How to apply**: the concrete mechanics.
  - **Anti-patterns**: named wrong approaches that the rule prevents.
- **Closing cross-references**: a table of related skills and entities, with the reason that this entity depends on or complements each one.

## References vs. examples — conditional need, not line count

Split content out into `references/*.md` or `examples/*.md` only for a part that applies conditionally: to only one of several invocation branches, target types, or flag combinations. Do not split because `SKILL.md` crossed some line-count threshold.

Two data points from this marketplace, in opposite directions:

- Some single-file skills with no subfolder run to about 500 lines or more. Every part of their content applies to every invocation.
- A skill of only about 150 lines can still justify a `references/` split. The condition: a large part of its content applies to only one of several branches. Examples are one target type out of eight, or one disposition out of six. Without the split, every reader scrolls past content that does not apply to their case.

## Author-commit-pairing discipline

Ship an authored or edited entity as at least two commits:

1. An **"Add X"** (or "Edit X") commit with the initial content of the entity.
2. An **"Apply review findings"** commit, after a review pass (Phase 7). Its body cites numbered findings `F1`/`F2`/`F3`/..., and each finding traces to a `source: <file>:<line>` citation.

Phase 2 uses the same `source:` citation format for rule extraction. Use the citation for the review and the fixes of this session. With it, the fixer and the reviewer can trace a generalized rule back to its exact file and line while the run is live. Do not present it as a stable, permanent commit-message convention. The cited file often lives in the personal `<claude-root>` configuration of the user, outside any repo (a memory file, a global CLAUDE.md). A future reader of the git history of the shipped repo cannot resolve it.

## Version bump

Phase 8 of `SKILL.md` sets the bump rules, the severities, and the precedent of the double bump in the middle of a run. Nothing here overrides them. The removal of `/review-loop` and `/review-pr` above is the concrete MAJOR case.

## Extend vs. create

Before you author a new entity in Phase 6, apply the gap-vs-overlap check of Step 7 in `references/classification-framework.md` again. Step 7 runs before Phase 4 proposes a destination. Phase 6 is where the choice of skill, command, or agent acts on its answer. For an overlap, extend the existing entity (an additional `## Rule N` section, an additional reference file). Do not author a near-duplicate.
