# vasar-plugins-marketplace

[![Tests](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml) [![Latest release](https://img.shields.io/github/v/release/Vasar007/vasar-plugins-marketplace)](https://github.com/Vasar007/vasar-plugins-marketplace/releases/latest) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Claude Code plugin marketplace](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-D97757.svg)](https://code.claude.com/docs/en/plugin-marketplaces)

This is a personal [Claude Code](https://code.claude.com/docs/en/overview) marketplace. Its plugins help with everyday development: generic developer workflows with a gated task pipeline, a writing style for technical documents, and a .NET backend toolkit.

The plugins are generic. Only `dotnet-backend-dev` is for a specific stack.

## Plugins

| Plugin | Group | Version | Purpose |
|---|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fessentials%2Fdev-essentials%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Cross-stack workflows for everyday development with Claude Code. They help you plan, implement, review, and document changes, and keep git and pull requests in order. |
| [`doc-styles`](./essentials/doc-styles) | `essentials` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fessentials%2Fdoc-styles%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | A writing style for technical documents. Its skill writes and rewrites docs as Markdown in the style of the OpenBSD manual pages. You must name that style to start it, for example "OpenBSD style" or "like a man page". It sets no style for chat replies. A hook checks each document in that style after a write. The hook needs `python3` on `PATH`. Without it, the hook does nothing. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fdotnet%2Fdotnet-backend-dev%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Skills, a command, and an agent for .NET backend services that use Clean Architecture, DDD, and EF Core. They create the usual parts of such a service and its tests, and follow one hub of backend conventions. Most templates assume a private shared framework of guard and wrapper types. |
| [`kb`](./knowledge/kb) | `knowledge` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fknowledge%2Fkb%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Wiring for a personal knowledge base kept in git. Hooks sync the knowledge base, print its indexes, guard note writes, approve read-only commands, and brief subagents. Skills capture a solved problem and close a task. It needs a local clone of the knowledge base. |

## Installing the marketplace

Add the marketplace to get access to all plugins at once. You can add it with a command or in a configuration file.

To add the marketplace with a command, run:

```text
/plugin marketplace add https://github.com/Vasar007/vasar-plugins-marketplace
```

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
/plugin install doc-styles@vasar-plugins-marketplace
/plugin install dotnet-backend-dev@vasar-plugins-marketplace
/plugin install kb@vasar-plugins-marketplace
```

`dotnet-backend-dev` uses skills and agents of `dev-essentials`, so it declares it as a dependency. If you install it, Claude Code also installs `dev-essentials`.

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

The page [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) gives the details. The page [When auto-update runs](https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs) gives the timing.

## Working across sessions

After a long pause, a long session costs more than a new session that reads a hand-off file. The page [Working across sessions](./docs/workflows.md) covers the choice between one session and a new one. It also gives the costs that eval runs measured.

## Rules for push, force push, and --no-verify

Some skills of this marketplace push, and some of them say never to force-push or to pass `--no-verify`. These rules are text in the skills. A plugin cannot ship permission rules, so the plugins cannot enforce them. To enforce these rules, add the rules in [`docs/permissions.md`](./docs/permissions.md) to your own configuration file, for example `~/.claude/settings.json`.

## Contributing

These guides in `docs/` are for readers who change this marketplace or add a plugin. They give only the rules of this repository. The official documentation describes the rest.

- [Authoring reference](./docs/authoring.md): the folder structure, the rules for `marketplace.json` and `plugin.json`, the conventions, and the validator. Before you push, run `claude plugin validate .` from the repository root. Then run `claude plugin validate ./<group>/<plugin>` for each plugin that you changed.
- [Testing](./docs/testing.md): the parts of the test run and the CI workflow `.github/workflows/tests.yml`. To run all tests, run `python3 -m unittest discover -s tests -v` from the repository root. If you add a new `.md` file, run `git add` on it first, because the linters read only the files that git tracks.
- [Evals](./docs/evals.md): the eval cases, the compare script `tests/evals/compare_versions.py`, and the behavior suites. Each eval run calls a model on your account, so CI does not run the evals.

See [`CHANGELOG.md`](./CHANGELOG.md) for the changes in each release.

## References

- [Install and manage plugins](https://code.claude.com/docs/en/plugins/install): install scopes, private marketplaces, and updates.
- [Create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace): plugin entries, plugin sources, and validation.
- [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference): all fields of `marketplace.json`.
- [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference): all fields of `plugin.json` and the standard layout of a plugin.
- [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading): the plugin cache, the version of a plugin, and automatic updates.
- [Plugin commands reference](https://code.claude.com/docs/en/plugins/cli-reference): the `claude plugin` commands, `/plugin`, and `/reload-plugins`.
- [Configuration reference](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces): the configuration keys `extraKnownMarketplaces` and `enabledPlugins`.
