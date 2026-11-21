# vasar-plugins-marketplace

[![Tests](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml) [![Latest release](https://img.shields.io/github/v/release/Vasar007/vasar-plugins-marketplace)](https://github.com/Vasar007/vasar-plugins-marketplace/releases/latest) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Claude Code plugin marketplace](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-D97757.svg)](https://code.claude.com/docs/en/plugin-marketplaces)

This is a personal [Claude Code](https://code.claude.com/docs/en/overview) marketplace for developers who use Claude Code every day. It holds these plugins: `dev-essentials`, `doc-styles`, `dotnet-backend-dev`, and `kb`. They give generic developer workflows with a gated task pipeline and a writing style for technical documents. They add a .NET backend toolkit and the wiring for a personal knowledge base.

The plugins are generic, except `dotnet-backend-dev`. It is for a .NET backend, and most of its templates assume a private shared framework of guard and wrapper types.

## Install

Run these commands in a Claude Code session:

```text
/plugin marketplace add Vasar007/vasar-plugins-marketplace
/plugin install dev-essentials@vasar-plugins-marketplace
```

The install command opens the details of the plugin. Read what the plugin adds, then choose a scope. If the panel warns that the plugin stays pending, run `/reload-plugins --force`. To install another plugin, use its name from the table below. The page [Installing and updating](./docs/installing.md) gives the shell form and the configuration file for a project.

## Plugins

| Plugin | Group | Version | Purpose |
|---|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fessentials%2Fdev-essentials%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Cross-stack workflows to plan, implement, review, and document changes, and to keep git and pull requests in order. |
| [`doc-styles`](./essentials/doc-styles) | `essentials` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fessentials%2Fdoc-styles%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | A writing style for technical documents. Its skill writes and rewrites Markdown docs in the style of the OpenBSD manual pages. You must name the style to start it, for example "OpenBSD style" or "like a man page". It sets no style for chat replies. A hook checks each such document after a write. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fdotnet%2Fdotnet-backend-dev%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Skills, a command, and an agent for .NET backend services with Clean Architecture, DDD, and EF Core. They create the usual parts of a service and its tests, and follow its backend conventions. It declares `dev-essentials` as a dependency. |
| [`kb`](./knowledge/kb) | `knowledge` | ![version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FVasar007%2Fvasar-plugins-marketplace%2Fmain%2Fknowledge%2Fkb%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version) | Wiring for a personal knowledge base kept in git. Hooks sync the knowledge base, print its indexes, guard note writes, approve read-only commands, and brief subagents. Skills capture a solved problem and close a task. |

## Try it

After the install, type one of these first. None of them pushes or deletes. A step that writes a file says so.

| Plugin | First step | Result |
|---|---|---|
| `dev-essentials` | `/dev-essentials:help-review-pr <pull request URL>` | Run it in a clone of the repository of the pull request. Claude reviews the pull request and writes an HTML report. It edits no code and posts no comment unless you pass `--post` with a value, such as `--post=all`. |
| `doc-styles` | "Review this document against the OpenBSD style." | Claude reports each difference from the style. |
| `dotnet-backend-dev` | "Review this controller against the .NET backend conventions." | Claude loads the hub of conventions and compares the controller. |
| `kb` | `/kb:setup` | Claude scans the setup, changes nothing, and lists each missing piece. It shows each change and waits for your yes. |

## Requirements

All plugins need Claude Code. These plugins need more:

- `dev-essentials`: The units that read or post pull requests call the GitHub MCP server (the tools `mcp__plugin_github_github__*`). The `github` plugin of the official marketplace adds it: `/plugin install github@claude-plugins-official`. Some units, for example `bug-hunt`, `review-loop`, and `merge-worktree-projects`, run Python 3 scripts. They need a POSIX shell and Python 3 (Git Bash on Windows). Some units use git.
- `doc-styles`: The hook needs `python3` on `PATH`. Without it, the hook does nothing.
- `dotnet-backend-dev`: The plugin is for a .NET backend. Its units build and test with the .NET SDK. It needs `dev-essentials`, and Claude Code installs that plugin with it.
- `kb`: The plugin needs Bash (Git Bash on Windows), git, and a local clone of the knowledge base. See the [README of `kb`](./knowledge/kb/README.md).

## Updating the plugins

A push to `main` does not change the plugins that you installed. If the `version` in the `plugin.json` of a plugin is new, an update gets the plugin. For the rules of a new version, see [Versioning Policy](./CLAUDE.md#versioning-policy). Automatic updates are off by default for this marketplace.

After a new release, open the "Marketplaces" tab of `/plugin`, select `vasar-plugins-marketplace`, and select "Update marketplace". Or run `claude plugin update <plugin>@vasar-plugins-marketplace` in your shell. Then run `/reload-plugins`.

The page [Installing and updating](./docs/installing.md#update-the-plugins) gives the details, including `/plugin marketplace update` and automatic updates.

## Safety

A plugin can run hooks and MCP servers on your computer, so read what a plugin adds before you install it. Anthropic reviews the plugins of its own plugin directory. That review does not cover a plugin that you add from a marketplace URL, such as this marketplace. So add such a plugin only from a source that you trust. Read [Plugin security and trust](https://code.claude.com/docs/en/plugins/security) and [Before you add a plugin](https://claude.com/docs/plugins/overview#before-you-add-a-plugin) for the details.

Some skills push, and some say never to force-push or to pass `--no-verify`. These rules are only text, because a plugin cannot ship permission rules. To enforce them, add the rules in [`docs/permissions.md`](./docs/permissions.md) to your own configuration file, for example `~/.claude/settings.json`.

## Documentation

| Page | What it covers |
|---|---|
| [Installing and updating](./docs/installing.md) | The shell form, the configuration files, and the steps for updates. |
| [Working across sessions](./docs/workflows.md) | The work modes of the workflows, one session or a new one, and the costs that evals measured. |
| [Rules for push, force push, and `--no-verify`](./docs/permissions.md) | The permission rules for the push rules of the skills. |
| [Authoring reference](./docs/authoring.md) | The folders, the rules for `marketplace.json` and `plugin.json`, and the validator. |
| [Testing](./docs/testing.md) | The test run and the CI workflow `.github/workflows/tests.yml`. |
| [Maintainer tools](./docs/tools.md) | The scripts in `tools/` for a merge of `main`, a release, the eval results, and the runs in WSL2. |
| [Evals](./docs/evals.md) | The eval cases, the script `tests/evals/compare_versions.py`, and the behavior suites. |
| [Official documentation](./docs/installing.md#official-documentation) | The official pages about plugins. |

## Contributing

The pages "Authoring reference", "Testing", and "Evals" of the documentation map are for readers who change this marketplace or add a plugin.

- Before you push, run `claude plugin validate .` from the repository root. Then run `claude plugin validate ./<group>/<plugin>` for each plugin that you changed.
- To run all tests, run `python3 -m unittest discover -s tests -v` from the repository root. If you add a new `.md` file, run `git add` on it first, because the linters read only the files that git tracks.
- Each eval run calls a model on your account, so CI does not run the evals.

See [`CHANGELOG.md`](./CHANGELOG.md) for the changes in each release.

## License

MIT. See [LICENSE](./LICENSE).
