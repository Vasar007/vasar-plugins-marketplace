# vasar-plugins-marketplace

[![Tests](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml) [![Latest release](https://img.shields.io/github/v/release/Vasar007/vasar-plugins-marketplace)](https://github.com/Vasar007/vasar-plugins-marketplace/releases/latest) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Claude Code plugin marketplace](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-D97757.svg)](https://code.claude.com/docs/en/plugin-marketplaces)

This is a personal [Claude Code](https://docs.claude.com/claude-code) marketplace. Its plugins help with everyday development: generic developer workflows, a .NET backend toolkit, and a gated pipeline that takes one task from plan to commit.

> This repository is private. Its artifacts are generic and stack-neutral. They carry no employer or product branding.

## Plugins

| Plugin | Group | Purpose |
|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | Cross-stack workflows for everyday development with Claude Code. They help you plan, implement, review, and document changes, and keep git and pull requests in order. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | Skills, a command, and an agent for .NET backend services that use Clean Architecture, DDD, and EF Core. They create the usual parts of such a service and its tests, and follow one hub of backend conventions. |
| [`gop-pipeline`](./workflows/gop-pipeline) | `workflows` | A gated pipeline that takes one coding task from plan to commit. It plans, implements, builds, and tests the change, reviews it with five validator agents in parallel, and then commits and pushes it. |

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
├── .github/
│   └── workflows/
│       └── tests.yml           # Runs the tests in CI
├── .markdownlint.jsonc         # markdownlint rules for the .md files
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
│       ├── agents/
│       ├── commands/
│       └── skills/
├── workflows/
│   └── gop-pipeline/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/
│       └── skills/
└── tests/                      # Repository tests, not part of a plugin
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

### Testing

The folder `tests/` holds the tests of this repository. It is outside every plugin folder, so Claude Code does not copy it into the plugin cache. The tests need Python 3 and Git. The markdownlint test also needs Node.js 22 or later, because it runs `markdownlint-cli` through `npx`.

To run all tests, run this command from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The command runs these parts:

- The tests of `check_report.py` (skill `bug-hunt`) and `trim_report.py` (skill `trim-artifacts`).
- The simple-english linter on every tracked `.md` file of the repository. A hit fails the test, unless `tests/simple-english-baseline.json` lists it. Each entry of that file gives the reason for the exception. A baseline entry without a hit also fails the test.
- markdownlint on every tracked `.md` file of the repository. The rules are in `.markdownlint.jsonc`. Each rule that the file turns off has a comment with the reason.

The two linters read only the files that git tracks. If you add a new `.md` file, run `git add` on it before you run the tests.

The simple-english test first looks for the linter in the folder that the variable `SIMPLE_ENGLISH_DIR` names. This is the root of a clone of SimpleEnglish. Then it looks in the plugin cache. If no linter is found, the test skips. The baseline is for simple-english 2.1.1, so another version can report other hits.

The workflow `.github/workflows/tests.yml` runs the same command on each pull request and on each push to `main`. In CI, a missing linter fails the run. CI uses the latest release of SimpleEnglish, so the linter version does not fall behind. If a new linter version makes the lint test fail, treat it as a blocker. Open an issue and fix it at once.

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
