# vasar-plugins-marketplace

This is a personal [Claude Code](https://docs.claude.com/claude-code) marketplace. It holds composer agents, workflow commands, and generic developer skills. It also holds a .NET backend toolkit and a full Git Operations Pipeline (GOP) workflow.

> This repository is private. Its artifacts are generic and stack-neutral. They carry no employer or product branding.

## Plugins

| Plugin | Group | Purpose |
|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | Composer agents (PR, Task, Test, Docs) and generic workflow commands. Cross-stack skills for markdown, XML docs, worktrees, PR review, feature pipeline, general conventions, personal-convention auditing, and artifact trimming. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | .NET, Clean Architecture, DDD, EF Core, and OpenAPI skills. A hub of backend conventions for controllers, services, configuration, domain models, EF patterns, logging, mappers, security, and testing. |
| [`gop-pipeline`](./workflows/gop-pipeline) | `workflows` | A pipeline with specialist validator subagents. The stages run in this order: plan, implement, build, test, validate, commit. The validate stage runs in parallel for correctness, reuse, security, compliance, and performance. |

## Installing the marketplace

Add the marketplace to get access to all plugins at once. You can add it with a command or in a configuration file.

To add the marketplace with a command, run:

```text
/plugin marketplace add https://github.com/Vasar007/vasar-plugins-marketplace
```

> The repository is private. Before Claude Code can clone it, configure a GitHub credential helper locally. You can use the SSH URL `git@github.com:Vasar007/vasar-plugins-marketplace.git` instead.

To add the marketplace in `.claude/settings.local.json`, use this configuration:

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

## Installing a single plugin

After you add the marketplace, install a single plugin by name:

```text
/plugin install dev-essentials@vasar-plugins-marketplace
/plugin install dotnet-backend-dev@vasar-plugins-marketplace
/plugin install gop-pipeline@vasar-plugins-marketplace
```

To enable specific plugins for a project automatically, extend the same `.claude/settings.local.json` file:

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

After you edit the configuration or install a plugin, run `/reload-plugins`. This loads the changes without a restart.

## Authoring reference

Only readers who modify this marketplace or add new plugins need this section.

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

A `source` path must start with `./`. It must resolve to a directory that contains `.claude-plugin/plugin.json`. Do not set `version` here. The version lives only in `plugin.json` (see [Versioning Policy](./CLAUDE.md#versioning-policy)).

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

Keep `plugin.json` to metadata only. Claude Code discovers components automatically at the documented default locations: `skills/<name>/SKILL.md`, `agents/<name>.md`, and `commands/<name>.md`.

The plugins in this marketplace do not set the fields `skills`, `agents`, or `commands`. The [Plugin manifest reference](https://code.claude.com/docs/en/plugins-reference) gives these rules for the fields:

- `skills` accepts a directory or an array of directories. The listed directories load together with the default `skills/` folder.
- `commands` accepts a file, a directory, an array of paths, or an object map. It replaces the default `commands/` folder.
- `agents` accepts only `.md` files, one or an array. It does not accept a directory. It replaces the default `agents/` folder.

Each path is relative to the plugin root and must start with `./`. If you add one of these fields, run the validator (see [Validating](#validating)).

### Validating

Before you push changes, run the bundled CLI validator:

```text
claude plugin validate .                       # validates marketplace.json
claude plugin validate ./<group>/<plugin>      # validates a single plugin manifest
```

## Conventions

- Names use `lowercase-kebab-case` and carry no organization or product prefix.
- Each skill has a `SKILL.md` file at the root of its `skills/<name>/` directory. Supporting files (templates, reference docs, stage scripts) sit alongside it.
- Each agent has one `.md` file under `agents/`.
- Each command has one `.md` file under `commands/`. The file name equals the slash-command name.
- A skill must declare stack-specific assumptions (for example .NET or PowerShell) explicitly inside the skill. Do not imply them across files.

See [`CHANGELOG.md`](./CHANGELOG.md) for the changes in each release.

## References

- [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces): the `marketplace.json` schema, source types, and version resolution.
- [Plugin manifest reference](https://code.claude.com/docs/en/plugins-reference): the `plugin.json` schema, component layout, and environment variables.
- [Discover and install plugins](https://code.claude.com/docs/en/discover-plugins): install workflows and the `extraKnownMarketplaces` and `enabledPlugins` configuration.
