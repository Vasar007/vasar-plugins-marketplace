# vasar-plugins-marketplace

Personal [Claude Code](https://docs.claude.com/claude-code) marketplace — composer agents, workflow commands, generic developer skills, a .NET backend toolkit, and a full Git Operations Pipeline (GOP) workflow.

> **Private repo.** Generic / stack-neutral artifacts. No employer or product branding.

---

## Plugins

| Plugin | Group | Purpose |
|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | Composer agents (PR, Task, Test, Docs) + generic workflow commands + cross-stack skills (markdown, XML docs, worktrees, PR review, feature pipeline, general conventions, artifact trimming) |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | .NET / Clean Arch / DDD / EF Core / OpenAPI skills + backend conventions hub (controllers, services, configuration, domain models, EF patterns, logging, mappers, security, testing) |
| [`gop-pipeline`](./workflows/gop-pipeline) | `workflows` | Plan → implement → build → test → validate (correctness/reuse/security/compliance/performance, in parallel) → commit pipeline with specialist validator subagents |

---

## Installing the marketplace

Gives access to all plugins at once.

**Via command:**

```text
/plugin marketplace add https://github.com/Vasar007/vasar-plugins-marketplace
```

> The repo is private. You'll need a GitHub credential helper (or SSH URL `git@github.com:Vasar007/vasar-plugins-marketplace.git`) configured locally before Claude Code can clone it.

**Via `.claude/settings.local.json`:**

```json
{
  "extraKnownMarketplaces": {
    "vasar-plugins-marketplace": {
      "source": {
        "source": "git",
        "url": "https://github.com/Vasar007/vasar-plugins-marketplace"
      }
    }
  }
}
```

---

## Installing a single plugin

After the marketplace is added, install a single plugin by name:

```text
/plugin install dev-essentials@vasar-plugins-marketplace
/plugin install dotnet-backend-dev@vasar-plugins-marketplace
/plugin install gop-pipeline@vasar-plugins-marketplace
```

Or auto-enable specific plugins for a project by extending the same `.claude/settings.local.json`:

```json
{
  "extraKnownMarketplaces": {
    "vasar-plugins-marketplace": {
      "source": {
        "source": "git",
        "url": "https://github.com/Vasar007/vasar-plugins-marketplace"
      }
    }
  },
  "enabledPlugins": {
    "dev-essentials@vasar-plugins-marketplace": true,
    "dotnet-backend-dev@vasar-plugins-marketplace": true
  }
}
```

After editing settings or installing, run `/reload-plugins` to pick up changes without restarting.

---

## Authoring reference

Only needed if you are modifying this marketplace or adding new plugins.

### Folder structure

```text
vasar-plugins-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Lists every plugin in this marketplace
├── essentials/
│   └── dev-essentials/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/
│       ├── commands/
│       └── skills/
├── dotnet/
│   └── dotnet-backend-dev/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
└── workflows/
    └── gop-pipeline/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── agents/
        └── skills/
```

### `marketplace.json` schema

```json
{
  "name": "vasar-plugins-marketplace",
  "description": "One-line summary shown in /plugin Discover tab",
  "owner": { "name": "Vasily Vasilyev", "email": "vasar007@gmail.com" },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./<group>/<plugin>",
      "description": "One-line summary shown when picking the plugin"
    }
  ]
}
```

`source` paths must start with `./` and resolve to a directory containing `.claude-plugin/plugin.json`. Do **not** set `version` here — it lives only in `plugin.json` (see [Versioning Policy](./CLAUDE.md#versioning-policy)).

### `plugin.json` schema

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin covers",
  "author": { "name": "Vasily Vasilyev", "email": "vasar007@gmail.com" },
  "repository": "https://github.com/Vasar007/vasar-plugins-marketplace",
  "keywords": ["topic", "another-topic"]
}
```

Keep `plugin.json` to metadata only. Claude Code auto-discovers components at the documented default locations: `skills/<name>/SKILL.md`, `agents/<name>.md`, and `commands/<name>.md`. Do **not** add `skills`, `agents`, or `commands` fields pointing at directory strings — those values are interpreted as file paths and cause the plugin to fail to load.

### Validating

Run the bundled CLI validator before pushing changes:

```text
claude plugin validate .                       # validates marketplace.json
claude plugin validate ./<group>/<plugin>      # validates a single plugin manifest
```

---

## Conventions

- Names: `lowercase-kebab-case`. No organization or product prefixes.
- Skill files: `SKILL.md` at the root of each `skills/<name>/` directory; supporting files (templates, reference docs, stage scripts) sit alongside it.
- Agent files: one `.md` per agent under `agents/`.
- Command files: one `.md` per command under `commands/`. Filename = slash-command name.
- Stack-specific assumptions (e.g. .NET, PowerShell) must be declared explicitly inside the skill, not implied across files.

See [`CHANGELOG.md`](./CHANGELOG.md) for what landed when.

---

## References

- [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) — `marketplace.json` schema, source types, version resolution
- [Plugins reference](https://code.claude.com/docs/en/plugins-reference) — `plugin.json` schema, component layout, environment variables
- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins) — install workflows and `extraKnownMarketplaces` / `enabledPlugins` settings
