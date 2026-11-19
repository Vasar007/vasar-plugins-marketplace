# Entity Authoring Conventions — Phase 6

Phase 6 of `SKILL.md` reads this file. The conventions come from an earlier ad-hoc promotion in the history of this marketplace (see the intro of `SKILL.md`).

## Contents

- Skill vs. command vs. agent selection
- Frontmatter: this skill's own template sticks to `name`, `description`, and `when_to_use`
- The description recipe
- Body structure
- General terms
- References vs. examples: conditional need and the 500-line limit
- Load-bearing terms
- Author-commit-pairing discipline
- Version bump
- Extend vs. create

---

## Skill vs. command vs. agent selection

The shapes grow in different ways. Pick the shape that the approved rules really need. Do not pick by habit, and do not default to a skill because "skills are more flexible".

- **Command**: a one-shot, single-file procedure that the user types, with no growth path. The user types `/plugin:name`, and the procedure runs once. Use a command for a fixed linear script with no branching phases and no reference-file depth.
- **Skill**: model-invoked. It triggers from a description match, not only from a typed command. It needs triggering and progressive disclosure, and it often needs multi-file depth (`references/`, `examples/`). Use a skill for content with phases, flags, or decision trees, or for content that grows over time.
- **Agent**: a persona with a restricted tool allowlist. Use an agent for content that works best as "a specialized worker with only these tools", not as instructions that the main session follows itself.

**Concrete precedent**. The history of this marketplace deleted the commands `/review-loop` and `/review-pr` in favor of the single skill `dev-essentials:review-loop`. Those commands outgrew the one-shot linear-script shape. They had phases, flags, and enough depth for reference files, which a single-file command cannot hold cleanly. The deletion is also the concrete MAJOR case of a version bump, because it removed existing invocation paths (`/review-loop`, `/review-pr`).

## Frontmatter: this skill's own template sticks to `name`, `description`, and `when_to_use`

The Claude Code skill frontmatter supports several optional fields beyond `name` and `description`. Examples are `allowed-tools`, `model`, `context`, `disable-model-invocation`, and `argument-hint`. The official Claude Code skills documentation has the full list. `dev-essentials:promote-conventions` sets `disable-model-invocation`, and `dev-essentials:feature-pipeline` sets `argument-hint` and `when_to_use`. Do not claim that skill frontmatter allows only two fields, or that an optional field is a schema error. It is not.

**By convention, the entity that this skill authors in Phase 6 uses only `name`, `description`, and `when_to_use`**. An agent gets no `when_to_use` (see the recipe below). The rules that this skill promotes are description-triggered procedures. They are not procedures that the user invokes by hand or that need restricted tools. If the authored entity needs the specific behavior of another optional field, add that field, for example `disable-model-invocation: true` for a workflow with side effects. Never add an optional field by default.

**`name` must equal the directory name, exactly**. The history of this marketplace had a real bug: the frontmatter `name` of a skill differed from the name of its directory. Make sure that each authored or edited skill keeps this invariant. It is a hard rule, not an edge case.

## The description recipe

Claude reads the `description` of a skill to decide whether to use the skill. Claude Code loads the descriptions of all skills, commands, and agents into every session. The skill listing has a budget of 1% of the context window. If the listing is over the budget, Claude Code drops the descriptions of the skills that you use least. Claude Code also cuts the `description` and `when_to_use` text of one skill at 1,536 characters. So keep each description short:

1. Put the main use case first, in one plain sentence. `description` says what the entity does.
2. Put the two to four strongest trigger phrases, in quotes, that a user can type. For a skill or a command, put them in `when_to_use`. Start it with "Use it", or with the condition that triggers the entity. For an agent, put them at the end of `description`.
3. Keep `description` and `when_to_use` together at 800 characters or fewer. Aim for 250 to 500 characters.
4. Keep the facts that change what the user expects from a run. Examples are a stop before a push or a post, a new GitHub issue, and a named exception to a rule. Word each fact in general terms.
5. If the entity exists for a library, a product, a type, a method, or a file, name it. Examples are .NET, EF Core, OpenAPI as a format, git for a git skill, and markdownlint for a skill about Markdown warnings. In all other cases, use a general term, for example "the generated client" and not the name of the code generator. Other projects use other tools and other names. This rule also applies to the body and to the `keywords` of `plugin.json`. A body names a replaceable tool only in a marked form. "General terms" below lists the forms. Only a plugin that exists for a tool can use the name of that tool as a keyword. Use one general term for each role in all files of the marketplace. The table in "General terms" below lists the terms. At its first use in a file, give an example with it, for example "the mocking library (for example, NSubstitute)".
6. Leave out the internal mechanics of the entity. Examples are tag names, report IDs, phase or bucket names, rule numbers, counts of reference files, and internal file names. Put them, and the other sub-topics and scenarios, in the body. A hub skill can name its topics in one sentence.
7. If only one skill dispatches an agent, say so in the description of the agent.
8. Do not put angle brackets (`<` and `>`) in `description`. claude.ai reads text such as `<name>` as an XML tag and removes the brackets. A placeholder in a path then disappears on claude.ai. Describe the placeholder in words, or put it in the body.

**Made-up example** of the shape (not a real skill in this marketplace):

```yaml
description: "Manage the rollout stages of feature flags for a web service."
when_to_use: "Use it for 'add a feature flag', 'promote this flag to 100%', or 'retire the flag for X'."
```

### When `when_to_use` helps

`when_to_use` holds the trigger phrases and the example requests. Claude Code appends it to `description` in the skill listing. Both fields count toward the same cap of 1,536 characters, so the split saves no characters. Its value is structure. `description` says what the entity does. `when_to_use` names the requests that trigger it.

- Skill or command: put the trigger phrases and a "Do not use it for X" line in `when_to_use`. A command accepts the same frontmatter fields as a skill, except `name` and `paths`.
- Agent: do not add `when_to_use`. The frontmatter of an agent has no such field, and Claude Code ignores an unknown field without a warning. Put the trigger phrases in `description`.
- Skill with `disable-model-invocation: true`: do not add `when_to_use`. Claude Code does not load the description of such a skill into the context, so the field has no effect.

## Body structure

- **H1 title**: the name of the skill in prose form.
- **Provenance preamble**, in this style: "This skill consolidates `<N>` rules that the user corrected the main agent on many times. They belong here, not only in personal memory." A skill that comes from another kind of precedent uses an equivalent frame. The intro of this skill is an example: it names the earlier ad-hoc promotion that the skill comes from.
- **`## Rule N — <imperative>`** sections. Each one has:
  - **Why**: the reasoning or the failure mode that makes the rule necessary.
  - **How to apply**: the concrete mechanics.
  - **Anti-patterns**: named wrong approaches that the rule prevents.
- **Closing cross-references**: a table of related skills and entities, with the reason that this entity depends on or complements each one.
- **Tool names**: item 5 of the description recipe also applies to the body. Keep the concrete guidance for the library of an example, and mark it in one of the forms of "General terms" below.

## General terms

Item 5 of the description recipe asks for a general term in place of a replaceable tool. A body names such a tool only in one of these marked forms:

- "for example, X", as in "the mocking library (for example, NSubstitute)".
- A bracket with the tool as its label, as in "(FluentValidation: `.SetValidator()`)".
- A section or a code block that says that it shows X, as in "The example uses the Cosmos DB provider of EF Core".
- A section or a paragraph for one tool that starts with a condition or a scope sentence. Examples are "If the project does not use Cosmos DB, skip this section" and "This gate is for NSubstitute as the mocking library".
- A sentence, a list item, or a bracket that starts with the tool as a condition: "With X,", "For X,", or "In X,", also in lower case. Examples are "With OpenSpec, run `openspec list`" and "(for NSwag, the `NSwagGeneration` item group)".

A label can come before a marked form, as in "**Fixture.Inject**: In AutoFixture, replace the default mock".

Item 5 also asks for one general term for each role. The table lists the general term of each role that the files use now. If a new role needs a term, add a row.

| Role | General term | Example names |
| --- | --- | --- |
| Runs the tests and gives the test attributes | the test framework | NUnit |
| Gives the assertion calls | the assertion library | FluentAssertions |
| Makes mocks and argument matchers | the mocking library | NSubstitute |
| Makes test data through a fixture | the test data library | AutoFixture |
| Generates converters between models | the mapping library | Riok.Mapperly |
| Runs the rules for the values of an options class | the validation library | FluentValidation |
| Generates code from the OpenAPI spec in the build | the OpenAPI code generator (short form after its first use in a file: the code generator) | NSwag |
| Lints the OpenAPI spec | the OpenAPI linter | Spectral |
| Stores the entities as documents | a document database | Cosmos DB |
| Connects EF Core to a database | the database provider | Cosmos DB, SQLite, the EF Core in-memory provider |
| Shows and edits the data in a database by hand | the data tool of the database | Cosmos DB Data Explorer |
| Sets the environment values of a deployment | the deployment system | Helm |
| Runs a spec-first change workflow | the spec framework | OpenSpec |
| Tracks issues and tasks | the task provider | GitHub Issues, Jira |
| Gives the cloud APIs for scripts | the cloud provider | AWS, Azure |
| Opens the files and the worktrees | the editor | VS Code, Rider |

## References vs. examples: conditional need and the 500-line limit

Split content out into `references/*.md` or `examples/*.md` in these cases:

1. A part applies conditionally: to only one of several invocation branches, target types, or flag combinations. A short `SKILL.md` does not change this. Example: a skill of only about 150 lines can need a `references/` split. A large part of it applies to one target type out of eight, or to one disposition out of six. Without the split, every reader scrolls past content that does not apply to their case.
2. `SKILL.md` grows past 500 lines. The whole `SKILL.md` loads into the context at each invocation, so a long file costs tokens and hides the important rules. After a compaction, Claude Code also keeps only the first 5,000 tokens of an invoked skill. So keep the rules for every invocation in `SKILL.md`, near the top. Move the detailed material out with one or more of the options below. In `SKILL.md`, say which file to read or run, and when.
   - Step references: move long tables, templates, worked examples, and the procedure of one step to `references/*.md`. The skill reads each file at the step that needs it.
   - Scripts: move a mechanical procedure into a script in `scripts/`. Claude Code runs the script, and the script text does not load into the context.
   - Agent files: move a role brief, for example of a reviewer or a fixer, into an agent file of the plugin (`agents/<name>.md`). The skill dispatches that agent. The brief loads only in the subagent, so the agent file must not depend on the text of the skill.
   - `context: fork` with `agent`: these two frontmatter fields run the whole skill in a subagent of the named type. Use them only for a skill with an explicit task. A skill that has only guidelines gives the subagent no task to act on.
   - An orchestrator skill: split the workflow into smaller skills, and keep one skill that invokes each of them with the Skill tool, in order.

## Load-bearing terms

Before you author the entities, pick the terms for each promoted rule. Pick them also for each superseded personal file of 9d. Pick one to three short phrases that the authored or shipped entity must hold for the rule to stay covered. Take them from the rule text of Phase 2, as the entity words it. Examples are a flag name, a field name, or the key phrase of the rule. Record them in the run state, and copy them into the TODO entry (9c.7). Precondition C and step 1 of 9d read them from there.

## Author-commit-pairing discipline

When the review loop fixes something, ship an authored or edited entity as an "Add X" commit plus the review-fix commits:

1. An **"Add X"** (or "Edit X") commit with the initial content of the entity.
2. The review-fix commits of Phase 7. A round that fixes nothing makes none. The review loop makes one `Review round <N>: Fix ...` commit for each round that fixes something. Do not rewrite or amend them. Keep the `F1`/`F2` numbering and the `source: <file>:<line>` citation of each finding in the "Review loop" section of the Phase 10 report. Do not put them in a commit message.

Phase 2 uses the same `source:` citation format for rule extraction. Use the citation for the review and the fixes of this session. With it, the fixer and the reviewer can trace a generalized rule back to its exact file and line while the run is live. Do not present it as a stable, permanent commit-message convention. The cited file often lives in the personal `<claude-root>` configuration of the user, outside any repo (a memory file, a global CLAUDE.md). A future reader of the git history of the shipped repo cannot resolve it.

## Version bump

Phase 8 of `SKILL.md` sets the bump rules, the severities, and the precedent of the double bump in the middle of a run. Nothing here overrides them. The removal of `/review-loop` and `/review-pr` above is the concrete MAJOR case.

## Extend vs. create

Before you author a new entity in Phase 6, apply the gap-vs-overlap check of Step 7 in `references/classification-framework.md` of `audit-personal-conventions` again. Step 7 runs before Phase 4 proposes a destination. Phase 6 is where the choice of skill, command, or agent acts on its answer. For an overlap, extend the existing entity (an additional `## Rule N` section, an additional reference file). Do not author a near-duplicate.
