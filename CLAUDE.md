# Claude Code Instructions

## Documentation First

When working with the Claude Code plugin system (skills, agents, hooks, frontmatter, slash commands, MCP, settings), **always verify against official documentation before making any claims**. Do not reason from first principles or guess. Look it up.

If you are unsure about a plugin system feature, use WebSearch / WebFetch to read the docs before you answer.

Do not say something is "not possible" or "not supported" without having verified it in the documentation.

## Versioning Policy

Each plugin sets an explicit `version` field in its `plugin.json`, and **only** there. Never set it in the marketplace entry, because `plugin.json` silently wins (see the [official docs](https://code.claude.com/docs/en/plugins/loading#how-claude-code-computes-the-version)). This gives deliberate control over the release scope. A push alone does **not** go to installed users. Only a version bump does.

**Bump rules** ([semver](https://semver.org)):

- **MAJOR** (`1.0.0` → `2.0.0`): breaking changes that alter existing invocation paths. Examples are removed or renamed skills, agents, or commands, reorganized invocation paths, and incompatible reference-file restructures. An old `/plugin:name` invocation becomes a silent no-op until the user updates.
- **MINOR** (`1.0.0` → `1.1.0`): new functionality added in a backward-compatible way. Examples are a new skill, agent, or command, an additive option in an existing skill, and new optional reference docs.
- **PATCH** (`1.0.0` → `1.0.1`): backward-compatible fixes only. Examples are typos, clarifications, prompt wording tweaks, fixed examples, manifest-metadata updates, and dependency-pin tweaks that do not change behavior.

**When to bump**: bump the version of the **affected plugin only** in the same commit/PR that ships the change. If a single PR touches multiple plugins, bump each affected plugin's `plugin.json`.

**What does not get bumped**: the marketplace itself (no `version` is set on `marketplace.json`), and any plugin whose files are unchanged in the PR.

**How users receive updates**: after the new version lands on `main`, users get it in one of these ways. They select "Update marketplace" for `vasar-plugins-marketplace` in the "Marketplaces" tab of `/plugin`. Or they run `claude plugin update <plugin>@vasar-plugins-marketplace` in a shell. Then they run `/reload-plugins`. If the `version` of a plugin is new, Claude Code replaces the cached copy of that plugin. Else the cached copy stays. Automatic updates are off by default for this marketplace. If a user turns them on, Claude Code updates the plugins after a session starts. The user then runs `/reload-plugins` or starts a new session. For the details, see [Update the plugins](./docs/installing.md#update-the-plugins).

**Validator note**: `claude plugin validate` accepts `version`. If a plugin manifest sets `version`, the validator gives no warning for it. So expect no warnings on the plugin manifests.

## Repo conventions

- This is a **personal** Claude Code marketplace in a public repository. Keep all artifacts (skills, agents, commands, READMEs) generic and stack-neutral. No company or product names of a workplace, no internal hostnames, no internal URLs.
- Skill / agent names use lowercase-kebab-case without organization prefixes.
- Each plugin lives at `<group>/<plugin>/` with its own `.claude-plugin/plugin.json`.
- Each plugin has an icon at `assets/icon.png` in its folder: a square PNG of 512 to 2048 px on each side, under 2 MB. `claude plugin validate` finds the file by this path. Do not set the `icon` field of `plugin.json`, because the claude.ai sync strips it and warns. `tests/test_claude_ai_sync.py` makes sure that the file is there and has this size. It also makes sure that `plugin.json` has no `icon` key. If the file is missing or is not a PNG or SVG, `claude plugin validate` reports `ICON_MISSING` or `ICON_INVALID` as a plugin directory warning. That warning does not fail a `--strict` run. The validator does not make sure that the size is right.
- New plugins must be registered in `.claude-plugin/marketplace.json` and the matrix in `README.md`.
- If a behavior depends on a specific tool or runtime (for example .NET, PowerShell, or AWS), document the assumption explicitly inside the skill. Do not spread it across files.

## New and imported units

A unit is a skill, an agent, or a command. Every new unit goes through this workflow before it merges. This includes a unit that comes from another repo or from another person.

1. Define the job. Write one sentence for the task that the unit solves. Name who starts it (the user, Claude, or both). Name the test that shows it is done. Search the existing units for the same job. If one exists, extend it instead of adding a second unit.
2. Fit the repo. Remove branding and internal links, and keep the credit to the source. Follow the conventions of this file and of `dev-essentials:optimize-skill`. Use a kebab-case name. Leave model versions out of the text. State each tool or runtime assumption in the unit. Keep the entry file short, and put the details in reference files.
3. Write the evals before you tune the unit. Add trigger cases: one where the unit must start, and a near-miss for each neighbor unit that shares its words. If the unit changes files or runs a workflow, add behavior cases. Each case has a planted problem and graders that make sure that the outcome is correct. The file [`docs/evals.md`](./docs/evals.md) says how.
4. Measure it. Record a baseline with the unit, and one without it. For a unit in an existing plugin, run `tests/evals/compare_versions.py run` with `--base` set to the commit before the unit and `--head` set to `HEAD`. The base has no such unit, so the run measures the unit. For a new plugin with no dependencies, run `claude plugin eval <plugin> --ablation with-without`. That flag removes the whole plugin, not one unit. For a new plugin with dependencies, the repo has no run without the plugin: record a `compare_versions.py baseline` at `HEAD`, and say so in the PR. If the unit does not beat the run without it, the unit does not add value. Fix it or drop it.
5. Optimize it with `dev-essentials:optimize-skill`. Move fixed steps into scripts with unit tests. Remove obsolete, repeated, or extra instructions, and any instruction that the run without the unit already follows. Keep the description short and exact, because it costs tokens in every session.
6. Measure it again. The scores must not drop. Record the cost and the time of the suite.
7. Review the change with `dev-essentials:review-loop`.
8. Ship it. For a new plugin, register it in `.claude-plugin/marketplace.json` and in the matrix of `README.md`. Then add the CHANGELOG entry, and bump the version of each changed plugin.

A large change to an existing unit goes through steps 3 to 7. When a new model comes out, run the suites of the main units again.
