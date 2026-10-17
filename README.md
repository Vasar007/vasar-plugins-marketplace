# vasar-plugins-marketplace

[![Tests](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml) [![Latest release](https://img.shields.io/github/v/release/Vasar007/vasar-plugins-marketplace)](https://github.com/Vasar007/vasar-plugins-marketplace/releases/latest) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Claude Code plugin marketplace](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-D97757.svg)](https://code.claude.com/docs/en/plugin-marketplaces)

This is a personal [Claude Code](https://code.claude.com/docs/en/overview) marketplace. Its plugins help with everyday development: generic developer workflows, a .NET backend toolkit, and a gated pipeline that takes one task from plan to commit.

> This repository is private. Its artifacts are generic and stack-neutral. They carry no employer or product branding.

## Plugins

| Plugin | Group | Purpose |
|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | Cross-stack workflows for everyday development with Claude Code. They help you plan, implement, review, and document changes, and keep git and pull requests in order. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | Skills, a command, and an agent for .NET backend services that use Clean Architecture, DDD, and EF Core. They create the usual parts of such a service and its tests, and follow one hub of backend conventions. |
| [`gop-pipeline`](./workflows/gop-pipeline) | `workflows` | A gated pipeline that takes one coding task from plan to commit. It plans, implements, builds, and tests the change, reviews it with five validator agents in parallel, and then commits it. Without --autonomous, the push waits for your approval. |

## Installing the marketplace

Add the marketplace to get access to all plugins at once. You can add it with a command or in a configuration file.

To add the marketplace with a command, run:

```text
/plugin marketplace add https://github.com/Vasar007/vasar-plugins-marketplace
```

> The repository is private. Before Claude Code can clone it, configure a GitHub credential helper locally. You can use the SSH URL `git@github.com:Vasar007/vasar-plugins-marketplace.git` instead. For the requirements of each method, see [Add a private marketplace](https://code.claude.com/docs/en/plugins/install#add-a-private-marketplace).

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

## Updating the plugins

A push to `main` does not change the plugins that you installed. Claude Code compares the `version` in the `plugin.json` of a plugin with the version of the installed copy. If the two versions are the same, the installed copy stays. For the rules of a new version, see [Versioning Policy](./CLAUDE.md#versioning-policy).

After a new release, run these commands in a Claude Code session:

```text
/plugin marketplace update vasar-plugins-marketplace
/reload-plugins
```

The first command refreshes the marketplace and gets the new plugin versions. The second command loads the new versions into the running session. If you do not run `/reload-plugins`, the next session loads the new versions. If a plugin stays at the old version, run `claude plugin update <plugin>@vasar-plugins-marketplace` in your shell. A running session then needs `/reload-plugins` to load the new version.

Claude Code can also update the plugins automatically. For this marketplace, automatic updates are off by default. To turn them on in a session, run `/plugin`, open the "Marketplaces" tab, select `vasar-plugins-marketplace`, and select "Enable auto-update". To turn them on in the configuration, add `"autoUpdate": true` next to `source` in the `extraKnownMarketplaces` entry of the marketplace.

This is the `.claude/settings.local.json` configuration with automatic updates:

```json
{
  "extraKnownMarketplaces": {
    "vasar-plugins-marketplace": {
      "source": {
        "source": "git",
        "url": "https://github.com/Vasar007/vasar-plugins-marketplace"
      },
      "autoUpdate": true
    }
  }
}
```

With automatic updates, Claude Code refreshes the marketplace in the background some minutes after your first message in a session. It updates the plugins on disk, but the running session keeps the old versions. To load the new versions, run `/reload-plugins` or start a new session.

The background update does not ask for credentials. The repository is private, so the update works only with a stored git credential or with an SSH key in `ssh-agent`. The pages [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) and [When auto-update runs](https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs) give the details.

## Authoring reference

Only readers who modify this marketplace or add new plugins need this section. The official documentation describes the files of a marketplace and of a plugin. This section gives only the rules of this repository.

### Folder structure

Each plugin is in the folder `<group>/<plugin>/`, for example `essentials/dev-essentials/`. The manifest of the plugin is `.claude-plugin/plugin.json`. The components are in the default folders `skills/`, `agents/`, and `commands/`. For the default layout of a plugin, see [Standard layout](https://code.claude.com/docs/en/plugins/manifest-reference#standard-layout).

These items at the repository root are not part of a plugin:

- `.claude-plugin/marketplace.json` lists every plugin of the marketplace.
- `.github/workflows/tests.yml` runs the tests in CI.
- `.markdownlint.jsonc` holds the markdownlint rules for the `.md` files.
- `tests/` holds the tests of the repository.

### Rules for `marketplace.json`

Each plugin has one entry in `.claude-plugin/marketplace.json` with the fields `name`, `source`, and `description`. The `source` path has the form `./<group>/<plugin>`. It must start with `./`. It must point to a folder that contains `.claude-plugin/plugin.json`. Do not set `version` here. The version is only in `plugin.json` (see [Versioning Policy](./CLAUDE.md#versioning-policy)). For all fields of the file, see the [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference).

### Rules for `plugin.json`

Keep `plugin.json` to metadata only: `$schema`, `name`, `version`, `description`, `author`, `repository`, and `keywords`. Copy the values of `$schema`, `author`, and `repository` from the `plugin.json` of an existing plugin of this marketplace, for example `essentials/dev-essentials/.claude-plugin/plugin.json`. The plugins of this marketplace do not set the fields `skills`, `agents`, or `commands`. Claude Code finds the components in their default folders. For all fields, see the [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference).

### Validating

Before you push changes, run the validator from the repository root:

```text
claude plugin validate .                       # validates marketplace.json
claude plugin validate ./<group>/<plugin>      # validates one plugin and its components
```

Run the second command for each plugin that you changed. The run on the repository root does not read the skill, agent, and command files of the plugins. For the flags and the exit codes, see [`plugin validate`](https://code.claude.com/docs/en/plugins/cli-reference#plugin-validate).

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

- [Install and manage plugins](https://code.claude.com/docs/en/plugins/install): install scopes, private marketplaces, and updates.
- [Create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace): plugin entries, plugin sources, and validation.
- [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference): all fields of `marketplace.json`.
- [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference): all fields of `plugin.json` and the standard layout of a plugin.
- [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading): the plugin cache, the version of a plugin, and automatic updates.
- [Plugin commands reference](https://code.claude.com/docs/en/plugins/cli-reference): the `claude plugin` commands, `/plugin`, and `/reload-plugins`.
- [Configuration reference](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces): the configuration keys `extraKnownMarketplaces` and `enabledPlugins`.
