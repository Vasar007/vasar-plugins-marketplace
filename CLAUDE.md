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

**How users receive updates**: after the new version lands on `main`, users run `/plugin marketplace update vasar-plugins-marketplace` (or have auto-update enabled), then `/reload-plugins`. Claude Code compares the resolved `version` against its cached copy and pulls only the bumped plugins.

**Validator note**: `claude plugin validate` accepts `version`. If a plugin manifest sets `version`, the validator gives no warning for it.

## Repo conventions

- This is a **personal** Claude Code marketplace. Keep all artifacts (skills, agents, commands, READMEs) generic and stack-neutral. No employer/product branding, no internal hostnames, no internal URLs.
- Skill / agent names use lowercase-kebab-case without organization prefixes.
- Each plugin lives at `<group>/<plugin>/` with its own `.claude-plugin/plugin.json`.
- New plugins must be registered in `.claude-plugin/marketplace.json` and the matrix in `README.md`.
- If a behavior depends on a specific tool or runtime (for example .NET, PowerShell, or AWS), document the assumption explicitly inside the skill. Do not spread it across files.
