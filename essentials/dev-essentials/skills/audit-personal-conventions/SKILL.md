---
name: audit-personal-conventions
description: "Audit personal Claude Code conventions (memory indexes, the rules of a KB clone, global and project CLAUDE.md files, and personal commands, agents, and skills). It classifies each rule and shows a triage of the rules that belong in a marketplace plugin. It changes no file."
when_to_use: "Use it for 'audit my memory', 'promote my memory to skills', or 'which of my rules belong in the marketplace'. Do not use it to turn one named rule into a skill."
---

# Audit Personal Conventions

Personal conventions grow without review. They mix project-local trivia, personal taste, rules that many sources repeat, and bug reports against shipped skills. This skill sorts them in one audit-and-triage workflow. It follows the workflow of an earlier ad-hoc promotion of personal memory into a marketplace.

**Hard requirement: no hardcoded marketplace or host name**. Each mention of "the marketplace" resolves from `--marketplace=` and from the `name` field of that `marketplace.json`. This holds for the skill text, its phase prompts, its output templates, and its examples. The target can be a different marketplace than the one that ships this skill. Do not name this marketplace, another specific marketplace, or a specific host in prose, templates, or examples. One exception: you can name the source marketplace of an external, optional tool that this skill mentions.

## When not to use

Do not use this skill to promote one rule that the user names directly, for example "turn this into a skill" about one paragraph. Write that entity by hand. If `skill-creator` is installed, you can use it instead. `skill-creator` is an official Anthropic plugin from the `claude-plugins-official` marketplace, and it does not ship with this plugin. This skill is for the audit and triage of many sources at once.

## Path resolution rule

Resolve the Claude config root from the `CLAUDE_CONFIG_DIR` environment variable. If that variable is not set, use the home directory of the user plus `/.claude`. Never hardcode a username, a drive letter, or an absolute path in the text, prompts, or examples of this skill. Write each path relative to the config root or to the repo root.

## Arguments

| Flag | Default | Meaning |
| --- | --- | --- |
| `--scope=<tokens>` | `all` | Tokens, combined with commas: `memory`, `kb`, `global-claude-md`, `project-claude-md`, `claude-md`, `personal-entities`, and `all`. `memory` is the `MEMORY.md` index of each project, and `kb` is the rules of a KB clone. `claude-md` is an alias for both CLAUDE.md tokens. `personal-entities` is the personal global `commands/`, `agents/`, and `skills/`. If `all` comes with another token, warn and use `all`. If a token is unknown, stop and list the valid tokens. |
| `--projects=auto\|none\|<list>` | `auto` | `auto` takes every directory under the projects folder of the config root (see Phase 0). It decodes each encoded name by probing candidate paths, collapses worktree siblings into their one real parent repo, and reports the collapse count. `none` means global sources only. A list accepts project names, decoded paths, or encoded directory names. If an entry does not resolve, stop. |
| `--exclude-projects=<list>` | empty | Remove these projects from the `auto` set. |
| `--marketplace=<path>` | auto-detect | The root of the target marketplace repo, which receives the promoted entities. It can be a different marketplace than the one that ships this skill. If the current working tree contains `.claude-plugin/marketplace.json`, auto-detect uses it. Else, stop and ask. |
| `--target-plugin=<name>` | none (ambiguous: ask) | The default destination plugin in the target marketplace. The triage can choose another plugin for each item. |
| `--min-evidence=<N>` | `1` | Present only the promotion candidates that at least N independent sources corroborate. |
| `--dispositions=<tokens>` | all | Filter for the triage that the run presents: `promote`, `promote-scoped`, `fix-shipped`, `prune`, `keep`. The tokens map to the dispositions: `promote`=C, `promote-scoped`=D, `fix-shipped`=E, `prune`=F, `keep`=A+B. `keep` covers both leave-alone dispositions, because the run never acts on them. The filter can hide `keep` items from the detail table, but the summary always counts them. |
| `--include-vendored` | off (bare) | Include the vendored or third-party CLAUDE.md files in personal repos, with a clear label. By default, the run excludes them. |
| `--dry-run` | off (bare) | Accepted for old invocations. The audit always stops after the triage. |

`--dry-run` wins over every rule of this section. With `--dry-run`, the run always stops after the triage. This also applies to a promote request.

A flag of the promotion, for example `--cross-repo`, `--resume`, `--delete-personal-entities`, or `--mode`, belongs to `promote-conventions`. Its command is `/dev-essentials:promote-conventions`. Say so. The old call still works only in these cases. The first case is `--resume`. Read `../promote-conventions/SKILL.md`, start at "Phase 0 for a resume run" of that file, and skip the audit. The second case is a promote request, with or without a flag of the promotion. A promote request asks the run to promote rules or to act on a triage. Examples are "promote my memory to skills" and "promote the recommended items". If this conversation already holds a Phase 4 triage, do not run the audit again. Else, run the audit first. Then read that file, and continue at its Phase 5 in the same run.

Any other request is a question or an audit. Examples are "audit my memory", "which of my rules belong in the marketplace?", and a call with no request text. It stops after the triage. If it carries a flag of the promotion or a `--mode`, it still stops there. A mode adds no steps.

Resolve each relative path of the promote file against the folder of `promote-conventions`. A `${...}` placeholder in that file stays unfilled. Treat it as an empty value, except for the branch prefix.

The configured branch prefix is `${user_config.branch_prefix}`. Set it with `/plugin configure` (see `plugin.json`). If the value still shows as a `${...}` placeholder, no value is saved. Then the configured branch prefix is empty. When this skill continues into the promote file, use this value as the configured branch prefix of that file.

## After the triage

Unless the request continues into `promote-conventions` (see above), this skill stops after the Phase 4 triage. The user asked for a list, not for new commits or a version bump. End every triage reply that stops with the command that continues. An example is `/dev-essentials:promote-conventions approve all promotes`. Add one line on the Phase 5 verbs: `approve`, `defer`, and `reject` take item numbers, and `approve all promotes` and `approve none` are the two shorthands. Only the user starts that skill with the command. The next message in the same chat can be a Phase 5 reply, such as `approve 1,3`. Then read `../promote-conventions/SKILL.md`. Resolve each relative path of that file against the folder of `promote-conventions`. Continue at its Phase 5 in the same run.

## Autonomy

The audit has no approval gate and changes no file. A promotion that continues from a promote request, from `--resume`, or from a reply follows the gates of `promote-conventions`. If the work cannot go on without an answer, ask the user. An example is a marketplace root that does not resolve. Do not ask in other cases.

## Guardrails

- Classify per rule, not per file. One source file often mixes dispositions.
- The `type:` frontmatter field is never a category signal by itself. Read the content.
- The corroboration count is the strongest promote signal. Always count it before you propose a new entity.
- An **E** disposition is never a new entity. It is always a fix to an existing shipped entity, and then the run prunes the source.
- Never assign a disposition to a wrapper personal entity before a full-text diff against its wrapped entity.

## References and examples

| File | When to read |
| --- | --- |
| `references/source-inventory.md` | Phase 0 and Phase 1: the discovery paths, decode-and-probe, the worktree-sibling collapse, the wrapper diff, and the structural landmines. |
| `references/classification-framework.md` | Phase 3: the full decision tree, the tie-breakers, and the calibration cases. |
| `references/report-templates.md` | Phase 4: the triage template. |
| `examples/fix-shipped-entity.md` | The E-disposition path, with worked cases from end to end. |

## Phases (the workflow)

### Phase 0 — Resolve scope

Parse the flags. Resolve the Claude config root with the path resolution rule above. Then resolve the root of the target marketplace.

If the user gave `--marketplace=`, use it. Else, auto-detect the current working tree by its `.claude-plugin/marketplace.json`. If neither resolves, stop and ask.

Before you build the project set, read `references/source-inventory.md`. Build the project set from `--projects` with its decode-and-probe procedure and its worktree-sibling collapse. Before you read any source file, show the resolved scope to the user:

- The scope tokens.
- The project count, the worktree-collapse count, and the encoded names that did not resolve.
- The marketplace path and name.
- The target plugin, or "none".

### Phase 1 — Inventory (read-only)

Phase 1 is read-only. No flag combination lets it change a file.

Follow `references/source-inventory.md`, which you read in Phase 0:

- The discovery paths for each source type. Dedupe the files by resolved absolute path, so that each file counts once.
- The decode-and-probe procedure for encoded project directory names.
- The worktree-sibling collapse. A collapsed repo counts as one independent source for each rule in Phase 3.
- The mandatory diff of each wrapper personal entity against the entity that it wraps.
- The structural landmines. Know them before you extract rules.

### Phase 2 — Extract atomic rules

Write one record for each RULE, not for each file. One CLAUDE.md file or rule file often mixes categories, so a classification per file gets the mixed cases wrong. Each record has these fields:

- A normalized one-line statement of the rule.
- A `source: <path>:<line>` citation. The Phase 10 report of `promote-conventions` uses the same format for the numbered review findings. With it, an authoring commit can trace a generalized rule back to its origin.
- The source class: memory index, KB rule, global CLAUDE.md, project CLAUDE.md, or personal entity.
- Each inheritance or scope qualifier from Phase 1, for example a nested CLAUDE.md that narrows or negates a parent rule.

### Phase 3 — Classify, cluster, corroborate

Read `references/classification-framework.md` now, and apply its Steps 1 to 7 and its calibration cases. In short:

1. **Corroborate first.** Count the independent sources of each cluster of equivalent rules. Repetition across sources is the strongest promote signal.
2. **Check the already-promoted status against the on-disk plugin manifests of the target marketplace.** Never trust the "migrated" claim of a memory index. Never trust the runtime skills listing either. It mixes the personal global skills of the user with the shipped skills of the marketplace, and only the file location tells them apart.
3. **Assign exactly one disposition** from this enum:
   - **A-local**: leave. Truly project-local, with no promotion value.
   - **B-taste**: leave, unless named evidence shows an established team code style.
   - **C-universal**: promote as a new entity, unscoped.
   - **D-scoped**: promote as a new entity, with the scope stated in the description of the entity.
   - **E-fix-shipped**: fix the existing shipped entity, then prune the source. Never a new entity. A phrase like "stopgap until X is updated" is a near-certain marker.
   - **F-stale**: prune or annotate. The run produces no new content.

Before you propose a new entity, also apply the B-vs-C tie-breaker (Step 3), the over-generalization screen (Step 6), and the gap-vs-overlap check (Step 7). Never use the `type:` frontmatter field as a category signal (Step 5).

### Phase 4 — Present the triage

Copy the Phase 4 triage template from `references/report-templates.md`. Fill every table, and replace the bracketed placeholders. Do not change the section structure.

## Cross-references

| Skill | Relationship |
| --- | --- |
| `dev-essentials:promote-conventions` | Phases 5 to 10. The user starts it after the triage. It authors the approved entities and cleans up the sources. |
| `dev-essentials:subagent-orchestration` | The dispatch rules for each multi-step task that this skill delegates. Without it in the target marketplace, decide each dispatch case by case. |
| `dev-essentials:write-markdown` | Each Markdown file that a run writes, for example a triage file. |
