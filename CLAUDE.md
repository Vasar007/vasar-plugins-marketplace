# Claude Code Instructions

## Documentation First

When working with the Claude Code plugin system (skills, agents, hooks, frontmatter, slash commands, MCP, settings), **always verify against official documentation before making any claims**. Do not reason from first principles or guess — look it up.

If you are unsure about a plugin system feature, use WebSearch / WebFetch to check the docs before answering.

Do not say something is "not possible" or "not supported" without having verified it in the documentation.

## Repo conventions

- This is a **personal** Claude Code marketplace. Keep all artifacts (skills, agents, commands, READMEs) generic and stack-neutral. No employer/product branding, no internal hostnames, no internal URLs.
- Skill / agent names use lowercase-kebab-case without organization prefixes.
- Each plugin lives at `<group>/<plugin>/` with its own `.claude-plugin/plugin.json`.
- New plugins must be registered in `.claude-plugin/marketplace.json` and the matrix in `README.md`.
- When adding behavior that depends on a specific tool/runtime (e.g. .NET, PowerShell, AWS), document the assumption explicitly inside the skill rather than spreading it across files.
