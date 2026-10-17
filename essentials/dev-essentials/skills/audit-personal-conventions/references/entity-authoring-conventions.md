# Entity Authoring Conventions — Phase 6

Phase 6 of `SKILL.md` reads this file. The conventions come from an earlier ad-hoc promotion in the history of this marketplace (see the intro of `SKILL.md`).

---

## Skill vs. command vs. agent selection

The three shapes grow in different ways. Pick the shape that the approved rules really need. Do not pick by habit, and do not default to a skill because "skills are more flexible".

- **Command**: a one-shot, single-file procedure that the user types, with no growth path. The user types `/plugin:name`, and the procedure runs once. Use a command for a fixed linear script with no branching phases and no reference-file depth.
- **Skill**: model-invoked. It triggers from a description match, not only from a typed command. It needs triggering and progressive disclosure, and it often needs multi-file depth (`references/`, `examples/`). Use a skill for content with phases, flags, or decision trees, or for content that grows over time.
- **Agent**: a persona with a restricted tool allowlist. Use an agent for content that works best as "a specialized worker with only these tools", not as instructions that the main session follows itself.

**Concrete precedent**. The history of this marketplace deleted the commands `/review-loop` and `/review-pr` in favor of the single skill `dev-essentials:review-loop`. Those commands outgrew the one-shot linear-script shape. They had phases, flags, and enough depth for reference files, which a single-file command cannot hold cleanly. The deletion is also the concrete MAJOR case of a version bump, because it removed existing invocation paths (`/review-loop`, `/review-pr`).

## Frontmatter: this skill's own template sticks to `name` and `description`

The Claude Code skill frontmatter supports several optional fields beyond `name` and `description`. Examples are `allowed-tools`, `model`, `context`, `disable-model-invocation`, and `argument-hint`. The official Claude Code skills documentation has the full list. `dev-essentials:feature-pipeline` sets `argument-hint` and `disable-model-invocation`. Do not claim that skill frontmatter allows only two fields, or that an optional field is a schema error. It is not.

**By convention, the entity that this skill authors in Phase 6 uses only `name` and `description`**. The rules that this skill promotes are description-triggered procedures. They are not procedures that the user invokes by hand or that need restricted tools. If the authored entity needs the specific behavior of an optional field, add that field, for example `disable-model-invocation: true` for a workflow with side effects. Never add an optional field by default.

**`name` must equal the directory name, exactly**. The history of this marketplace had a real bug: the frontmatter `name` of a skill differed from the name of its directory. Make sure that each authored or edited skill keeps this invariant. It is a hard rule, not an edge case.

## The description recipe

Claude reads the `description` of a skill to decide whether to use the skill. Claude Code loads the descriptions of all skills, commands, and agents into every session. The skill listing has a budget of 1% of the context window. If the listing is over the budget, Claude Code drops the descriptions of the skills that you use least. Claude Code also cuts the `description` and `when_to_use` text of one skill at 1,536 characters. So keep each description short:

1. Put the main use case first, in one plain sentence.
2. Add the two to four strongest trigger phrases, in quotes, that a user can type.
3. Keep `description` and `when_to_use` together at 800 characters or fewer. Aim for 250 to 500 characters.
4. Put the sub-topics, flags, and scenarios in the body, not in the description.
5. If only one skill dispatches an agent, say so in the description of the agent.

**Made-up example** of the shape (not a real skill in this marketplace):

> "Manage the rollout stages of feature flags for a web service. Use it for 'add a feature flag', 'promote this flag to 100%', or 'retire the flag for X'.

## Body structure

- **H1 title**: the name of the skill in prose form.
- **Provenance preamble**, in this style: "This skill consolidates `<N>` rules that the user corrected the main agent on many times. They belong here, not only in personal memory." A skill that comes from another kind of precedent uses an equivalent frame. The intro of this skill is an example: it names the earlier ad-hoc promotion that the skill comes from.
- **`## Rule N — <imperative>`** sections. Each one has:
  - **Why**: the reasoning or the failure mode that makes the rule necessary.
  - **How to apply**: the concrete mechanics.
  - **Anti-patterns**: named wrong approaches that the rule prevents.
- **Closing cross-references**: a table of related skills and entities, with the reason that this entity depends on or complements each one.

## References vs. examples: conditional need and the 500-line limit

Split content out into `references/*.md` or `examples/*.md` in two cases:

1. A part applies conditionally: to only one of several invocation branches, target types, or flag combinations. A short `SKILL.md` does not change this. Example: a skill of only about 150 lines can need a `references/` split. A large part of it applies to one target type out of eight, or to one disposition out of six. Without the split, every reader scrolls past content that does not apply to their case.
2. `SKILL.md` grows past 500 lines. The Claude Code docs say: "Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files." After a compaction, Claude Code also keeps only the first 5,000 tokens of an invoked skill. So keep the rules for every invocation in `SKILL.md`, near the top. Move the detailed material out with one or more of the options below. In `SKILL.md`, say which file to read or run, and when.
   - Step references: move long tables, templates, worked examples, and the procedure of one step to `references/*.md`. The skill reads each file at the step that needs it.
   - Scripts: move a mechanical procedure into a script in `scripts/`. Claude Code runs the script, and the script text does not load into the context.
   - Agent files: move a role brief, for example of a reviewer or a fixer, into an agent file of the plugin (`agents/<name>.md`). The skill dispatches that agent. The brief loads only in the subagent, so the agent file must not depend on the text of the skill.
   - `context: fork` with `agent`: these two frontmatter fields run the whole skill in a subagent of the named type. Use them only for a skill with an explicit task. The docs warn that a skill with guidelines only gives the subagent "no actionable prompt".
   - An orchestrator skill: split the workflow into smaller skills, and keep one skill that invokes each of them with the Skill tool, in order.

## Author-commit-pairing discipline

Ship an authored or edited entity as at least two commits:

1. An **"Add X"** (or "Edit X") commit with the initial content of the entity.
2. An **"Apply review findings"** commit, after a review pass (Phase 7). Its body cites numbered findings `F1`/`F2`/`F3`/..., and each finding traces to a `source: <file>:<line>` citation.

Phase 2 uses the same `source:` citation format for rule extraction. Use the citation for the review and the fixes of this session. With it, the fixer and the reviewer can trace a generalized rule back to its exact file and line while the run is live. Do not present it as a stable, permanent commit-message convention. The cited file often lives in the personal `<claude-root>` configuration of the user, outside any repo (a memory file, a global CLAUDE.md). A future reader of the git history of the shipped repo cannot resolve it.

## Version bump

Phase 8 of `SKILL.md` sets the bump rules, the severities, and the precedent of the double bump in the middle of a run. Nothing here overrides them. The removal of `/review-loop` and `/review-pr` above is the concrete MAJOR case.

## Extend vs. create

Before you author a new entity in Phase 6, apply the gap-vs-overlap check of Step 7 in `references/classification-framework.md` again. Step 7 runs before Phase 4 proposes a destination. Phase 6 is where the choice of skill, command, or agent acts on its answer. For an overlap, extend the existing entity (an additional `## Rule N` section, an additional reference file). Do not author a near-duplicate.
