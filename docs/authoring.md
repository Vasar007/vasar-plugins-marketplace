# Authoring reference

Only readers who modify this marketplace or add new plugins need this file. The official documentation describes the files of a marketplace and of a plugin. This file gives only the rules of this repository.

## Folder structure

Each plugin is in the folder `<group>/<plugin>/`, for example `essentials/dev-essentials/`. The manifest of the plugin is `.claude-plugin/plugin.json`. The components are in the default folders `skills/`, `agents/`, and `commands/`. For the default layout of a plugin, see [Standard layout](https://code.claude.com/docs/en/plugins/manifest-reference#standard-layout).

These items at the repository root are not part of a plugin:

- `.claude-plugin/marketplace.json` lists every plugin of the marketplace.
- `.gitattributes` makes GitHub count the `.md` files in the language statistics of the repository.
- `.github/workflows/tests.yml` runs the tests in CI.
- `.markdownlint.jsonc` holds the markdownlint rules for the `.md` files.
- `docs/` holds the guides for contributors and the permission rules for users.
- `tests/` holds the tests of the repository. `tests/evals/stubs/` holds the stand-in plugins of the eval cases. They are outside the plugin folders, because the claude.ai sync skips a plugin that holds a second `.claude-plugin/plugin.json`.

## Rules for `marketplace.json`

Each plugin has one entry in `.claude-plugin/marketplace.json` with the fields `name`, `source`, and `description`. The `source` path has the form `./<group>/<plugin>`. It must start with `./`. It must point to a folder that contains `.claude-plugin/plugin.json`. Do not set `version` here. The version is only in `plugin.json` (see [Versioning Policy](../CLAUDE.md#versioning-policy)). To remove a plugin, delete its entry and add `"<plugin>": null` to the top-level `renames` map. Do not delete an entry of `renames`, because Claude Code reads the map to move the users of old names. For all fields of the file, see the [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference).

## Rules for `plugin.json`

Keep `plugin.json` to metadata and dependencies: `name`, `version`, `description`, `author`, `repository`, `keywords`, `dependencies`, and `userConfig`. A plugin can use a skill or an agent of another plugin of this marketplace. Then list that plugin in `dependencies` by its bare name, for example `"dependencies": ["dev-essentials"]`. Do not add a version range. A range resolves against release tags of the form `<plugin>--v<version>`, and this repository has no such tags. For the field, see [Plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies). A plugin folder holds no other `.claude-plugin` folder, because the claude.ai sync skips such a plugin. Do not set `$schema`. Claude Code accepts it, but the claude.ai sync strips it and shows a warning. Copy the values of `author` and `repository` from the `plugin.json` of an existing plugin of this marketplace, for example `essentials/dev-essentials/.claude-plugin/plugin.json`. The plugins of this marketplace do not set the fields `skills`, `agents`, or `commands`. Claude Code finds the components in their default folders. For all fields, see the [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference).

## Conventions

- Names use `lowercase-kebab-case` and carry no organization or product prefix.
- Each skill has a `SKILL.md` file at the root of its `skills/<name>/` directory. Supporting files (templates, reference docs, stage scripts) sit alongside it.
- Each agent has one `.md` file under `agents/`.
- Each command has one `.md` file under `commands/`. The file name equals the slash-command name.
- A skill must declare stack-specific assumptions (for example .NET or PowerShell) explicitly inside the skill. Do not imply them across files.

## Validating

Before you push changes, run the validator from the repository root:

```text
claude plugin validate .                       # validates marketplace.json
claude plugin validate ./<group>/<plugin>      # validates one plugin and its components
```

Run the second command for each plugin that you changed. The run on the repository root does not read the skill, agent, and command files of the plugins. For the flags and the exit codes, see [`plugin validate`](https://code.claude.com/docs/en/plugins/cli-reference#plugin-validate).
