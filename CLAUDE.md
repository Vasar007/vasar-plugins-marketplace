# Claude Code Instructions

## Documentation First

When working with the Claude Code plugin system (skills, agents, hooks, frontmatter, slash commands, MCP, settings), **always verify against official documentation before making any claims**. Do not reason from first principles or guess — look it up.

If you are unsure about a plugin system feature, use WebSearch / WebFetch to check the docs before answering.

Do not say something is "not possible" or "not supported" without having verified it in the documentation.

## Versioning Policy

Each plugin sets an explicit `version` field in its `plugin.json` (and **only** there — never in the marketplace entry, since `plugin.json` silently wins per the [official docs](https://code.claude.com/docs/en/plugins/loading#how-claude-code-computes-the-version)). This gives deliberate control over release scope: every push does **not** automatically propagate to installed users; only a version bump does.

**Bump rules** ([semver](https://semver.org)):

- **MAJOR** (`1.0.0` → `2.0.0`) — breaking changes that alter existing invocation paths: removed or renamed skills, agents, or commands (old `/plugin:name` invocations become silent no-ops until the user updates); reorganized invocation paths; incompatible reference-file restructures.
- **MINOR** (`1.0.0` → `1.1.0`) — new functionality added in a backward-compatible way: a new skill/agent/command, an additive option in an existing skill, new optional reference docs.
- **PATCH** (`1.0.0` → `1.0.1`) — backward-compatible fixes only: typos, clarifications, prompt wording tweaks, fixed examples, dependency-pin tweaks that don't change behavior, manifest-metadata updates.

**When to bump**: bump the version of the **affected plugin only** in the same commit/PR that ships the change. If a single PR touches multiple plugins, bump each affected plugin's `plugin.json`.

**What does not get bumped**: the marketplace itself (no `version` is set on `marketplace.json`), and any plugin whose files are unchanged in the PR.

**How users receive updates**: after the new version lands on `main`, users run `/plugin marketplace update vasar-plugins-marketplace` (or have auto-update enabled), then `/reload-plugins`. Claude Code compares the resolved `version` against its cached copy and pulls only the bumped plugins.

**Validator note**: `claude plugin validate` accepts `version` and is silent when it is set — so no warnings are expected on plugin manifests.

## Repo conventions

- This is a **personal** Claude Code marketplace. Keep all artifacts (skills, agents, commands, READMEs) generic and stack-neutral. No employer/product branding, no internal hostnames, no internal URLs.
- Skill / agent names use lowercase-kebab-case without organization prefixes.
- Each plugin lives at `<group>/<plugin>/` with its own `.claude-plugin/plugin.json`.
- New plugins must be registered in `.claude-plugin/marketplace.json` and the matrix in `README.md`.
- When adding behavior that depends on a specific tool/runtime (e.g. .NET, PowerShell, AWS), document the assumption explicitly inside the skill rather than spreading it across files.
