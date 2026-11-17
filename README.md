# vasar-plugins-marketplace

[![Tests](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml) [![Latest release](https://img.shields.io/github/v/release/Vasar007/vasar-plugins-marketplace)](https://github.com/Vasar007/vasar-plugins-marketplace/releases/latest) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Claude Code plugin marketplace](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-D97757.svg)](https://code.claude.com/docs/en/plugin-marketplaces)

This is a personal [Claude Code](https://code.claude.com/docs/en/overview) marketplace. Its plugins help with everyday development: generic developer workflows with a gated task pipeline, a writing style for technical documents, and a .NET backend toolkit.

It holds four plugins: `dev-essentials`, `doc-styles`, `dotnet-backend-dev`, and `kb`. The plugins are generic. Only `dotnet-backend-dev` is for a specific stack, and most of its templates assume a private shared framework of guard and wrapper types.

## Install

Run these commands in a Claude Code session:

```text
/plugin marketplace add Vasar007/vasar-plugins-marketplace
/plugin install dev-essentials@vasar-plugins-marketplace
```

The install command opens the details of the plugin. Read what the plugin adds, then choose a scope. To install another plugin, use its name from the table below. The page [Installing and updating](./docs/installing.md) gives the shell form, the configuration file for a project, and the steps for each plugin.

## Plugins

| Plugin | Group | Version | Purpose |
|---|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fessentials%2Fdev-essentials%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Cross-stack workflows for everyday development with Claude Code. They help you plan, implement, review, and document changes, and keep git and pull requests in order. |
| [`doc-styles`](./essentials/doc-styles) | `essentials` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fessentials%2Fdoc-styles%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | A writing style for technical documents. Its skill writes and rewrites docs as Markdown in the style of the OpenBSD manual pages. You must name that style to start it, for example "OpenBSD style" or "like a man page". It sets no style for chat replies. A hook checks each document in that style after a write. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fdotnet%2Fdotnet-backend-dev%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Skills, a command, and an agent for .NET backend services that use Clean Architecture, DDD, and EF Core. They create the usual parts of such a service and its tests, and follow one hub of backend conventions. It uses skills and agents of `dev-essentials`, so it declares that plugin as a dependency. |
| [`kb`](./knowledge/kb) | `knowledge` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fknowledge%2Fkb%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Wiring for a personal knowledge base kept in git. Hooks sync the knowledge base, print its indexes, guard note writes, approve read-only commands, and brief subagents. Skills capture a solved problem and close a task. |

If you install `dotnet-backend-dev`, Claude Code also installs `dev-essentials`.

## Try it

After the install, type one of these first. Each one reads or plans, and none of them pushes or deletes.

| Plugin | First step | Result |
|---|---|---|
| `dev-essentials` | `/dev-essentials:help-review-pr <pull request URL>` | Claude reviews the pull request and writes an HTML report. It edits no code and posts no comment unless you pass a `--mode` that posts. |
| `doc-styles` | "Review this document against the OpenBSD style." | Claude compares the document with the style and reports each difference. |
| `dotnet-backend-dev` | "Review this controller against the .NET backend conventions." | Claude loads the hub of conventions and compares the controller with it. |
| `kb` | `/kb:setup` | Claude runs a scan that changes nothing and lists each missing piece of the setup. It shows each change and waits for your yes. |

## Requirements

All plugins need Claude Code. These plugins need more:

- `dev-essentials`: The units that read or post pull requests call the GitHub MCP server (the tools `mcp__plugin_github_github__*`). Some units run Python 3 scripts, for example `bug-hunt`, `review-loop`, and `merge-worktree-projects`. These units need a POSIX shell and Python 3. On Windows, use Git Bash. Some units use git.
- `doc-styles`: The hook needs `python3` on `PATH`. Without it, the hook does nothing.
- `dotnet-backend-dev`: The plugin is for a .NET backend. It needs `dev-essentials`, and Claude Code installs that plugin with it.
- `kb`: The plugin needs Bash (Git Bash on Windows) and a local clone of the knowledge base. See the [README of `kb`](./knowledge/kb/README.md).

## Updating the plugins

A push to `main` does not change the plugins that you installed. A new version number in the `plugin.json` of a plugin does. For the rules of a new version, see [Versioning Policy](./CLAUDE.md#versioning-policy).

After a new release, run `/plugin` in a session, open the "Marketplaces" tab, select `vasar-plugins-marketplace`, and select "Update marketplace". Or run `claude plugin update <plugin>@vasar-plugins-marketplace` in your shell. Then run `/reload-plugins`.

The command `/plugin marketplace update vasar-plugins-marketplace` refreshes the listing of the marketplace. The docs do not say that it also updates the installed plugins. The page [Installing and updating](./docs/installing.md#update-the-plugins) gives the details and the steps for automatic updates.

## Safety

A plugin can run hooks and MCP servers on your computer, so read what a plugin adds before you install it. The page [Plugin security and trust](https://code.claude.com/docs/en/plugins/security) gives the details. The review of Anthropic does not cover a plugin that you add from a marketplace URL. So add such a plugin only from a source that you trust. The section [Before you add a plugin](https://claude.com/docs/plugins/overview#before-you-add-a-plugin) gives the details of this case.

Some skills of this marketplace push, and some of them say never to force-push or to pass `--no-verify`. These rules are text in the skills. A plugin cannot ship permission rules, so the plugins cannot enforce them. To enforce these rules, add the rules in [`docs/permissions.md`](./docs/permissions.md) to your own configuration file, for example `~/.claude/settings.json`.

## Documentation

| Page | What it covers |
|---|---|
| [Installing and updating](./docs/installing.md) | The shell form of the install, the configuration files, and the steps for updates and automatic updates. |
| [Working across sessions](./docs/workflows.md) | The choice between one session and a new one, and the costs that eval runs measured. |
| [Rules for push, force push, and `--no-verify`](./docs/permissions.md) | The permission rules that enforce the push rules of the skills. |
| [Authoring reference](./docs/authoring.md) | The folder structure, the rules for `marketplace.json` and `plugin.json`, the conventions, and the validator. |
| [Testing](./docs/testing.md) | The parts of the test run and the CI workflow `.github/workflows/tests.yml`. |
| [Evals](./docs/evals.md) | The eval cases, the compare script `tests/evals/compare_versions.py`, and the behavior suites. |
| [Install and manage plugins](https://code.claude.com/docs/en/plugins/install) | Official docs: install scopes, private marketplaces, and updates. |
| [Create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace) | Official docs: plugin entries, plugin sources, and validation. |
| [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) | Official docs: all fields of `marketplace.json`. |
| [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference) | Official docs: all fields of `plugin.json` and the standard layout of a plugin. |
| [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading) | Official docs: the plugin cache, the version of a plugin, and automatic updates. |
| [Plugin commands reference](https://code.claude.com/docs/en/plugins/cli-reference) | Official docs: the `claude plugin` commands, `/plugin`, and `/reload-plugins`. |
| [Configuration reference](https://code.claude.com/docs/en/settings-reference#extraknownmarketplaces) | Official docs: the configuration keys `extraKnownMarketplaces` and `enabledPlugins`. |

## Contributing

The guides [Authoring reference](./docs/authoring.md), [Testing](./docs/testing.md), and [Evals](./docs/evals.md) are for readers who change this marketplace or add a plugin. They give only the rules of this repository. The official documentation describes the rest.

- Before you push, run `claude plugin validate .` from the repository root. Then run `claude plugin validate ./<group>/<plugin>` for each plugin that you changed.
- To run all tests, run `python3 -m unittest discover -s tests -v` from the repository root. If you add a new `.md` file, run `git add` on it first, because the linters read only the files that git tracks.
- Each eval run calls a model on your account, so CI does not run the evals.

See [`CHANGELOG.md`](./CHANGELOG.md) for the changes in each release.

## License

MIT. See [LICENSE](./LICENSE).
