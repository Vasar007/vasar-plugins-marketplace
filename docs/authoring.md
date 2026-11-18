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
- `tools/` holds the scripts of the maintainers: the CHANGELOG step of a merge of `main`, the readers of eval results, and the WSL2 runners. No plugin ships them. See [Maintainer tools](tools.md).
- `tests/` holds the tests of the repository. `tests/evals/stubs/` holds the stand-in plugins of the eval cases. They are outside the plugin folders, because the claude.ai sync skips a plugin that holds a second `.claude-plugin/plugin.json`.

## Rules for `marketplace.json`

Each plugin has one entry in `.claude-plugin/marketplace.json` with the fields `name`, `source`, and `description`. The `source` path has the form `./<group>/<plugin>`. It must start with `./`. It must point to a folder that contains `.claude-plugin/plugin.json`. Do not set `version` here. The version is only in `plugin.json` (see [Versioning Policy](../CLAUDE.md#versioning-policy)). To remove a plugin, delete its entry and add `"<plugin>": null` to the top-level `renames` map. Do not delete an entry of `renames`, because Claude Code reads the map to move the users of old names. For all fields of the file, see the [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference).

## Rules for `plugin.json`

Keep `plugin.json` to metadata and dependencies: `name`, `version`, `description`, `author`, `repository`, `keywords`, `dependencies`, and `userConfig`. A plugin can use a skill or an agent of another plugin of this marketplace. Then list that plugin in `dependencies` by its bare name, for example `"dependencies": ["dev-essentials"]`. Do not add a version range. A range resolves against release tags of the form `<plugin>--v<version>`, and this repository has no such tags. For the field, see [Plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies). A plugin folder holds no other `.claude-plugin` folder, because the claude.ai sync skips such a plugin. Do not set `$schema` or `icon`. Claude Code accepts both, but the claude.ai sync strips them and shows a warning. The icon of a plugin is the file `assets/icon.png`, and `claude plugin validate` finds it by this path. Copy the values of `author` and `repository` from the `plugin.json` of an existing plugin of this marketplace, for example `essentials/dev-essentials/.claude-plugin/plugin.json`. The plugins of this marketplace do not set the fields `skills`, `agents`, or `commands`. Claude Code finds the components in their default folders. For all fields, see the [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference).

## Conventions

- Names use `lowercase-kebab-case` and carry no organization or product prefix.
- Each skill has a `SKILL.md` file at the root of its `skills/<name>/` directory. Supporting files (templates, reference docs, stage scripts) sit alongside it.
- Each agent has one `.md` file under `agents/`.
- Each command has one `.md` file under `commands/`. The file name equals the slash-command name.
- A skill must declare stack-specific assumptions (for example .NET or PowerShell) explicitly inside the skill. Do not imply them across files.
- A Python script reads its command-line arguments with `argparse`, so that each script has `--help` and the same error form. The one exception is `tests/evals/stubs/simple-english/evals/ste_lint.py`. It is a byte copy of the linter of the simple-english repository, and it changes there first.

## Validating

Before you push changes, run the validator from the repository root:

```text
claude plugin validate .                       # validates marketplace.json
claude plugin validate ./<group>/<plugin>      # validates one plugin and its components
```

Run the second command for each plugin that you changed. The run on the repository root does not read the skill, agent, and command files of the plugins. For the flags and the exit codes, see [`plugin validate`](https://code.claude.com/docs/en/plugins/cli-reference#plugin-validate).

## Rules of the claude.ai sync

The owner adds this marketplace to claude.ai with "Add marketplace". The sync reads the `main` branch. The sync has rules that `claude plugin validate` does not check, and its docs do not list all of them. This list names each rule that a sync or the docs showed so far. `tests/test_claude_ai_sync.py` tests each rule except the name rule and the last one. `tests/test_plugin_cli.py` tests the name rule with `claude plugin validate --strict`:

- `plugin.json` uses only the keys that a sync took with no warning. The sync stripped `$schema` and `icon` and warned, although the manifest reference documents both keys. No source lists the keys that the sync takes. So any other key can get the same warning until a sync takes it.
- `marketplace.json` and its plugin entries use only the keys that a sync took with no warning.
- The `description` of a skill, an agent, or a command holds no angle brackets. claude.ai reads them as XML tags and removes them.
- A plugin folder holds no other `.claude-plugin` folder. The sync skips such a plugin.
- A plugin folder has no top-level `bin/` folder. claude.ai rejects such a plugin. See [Keep executables out of the top-level bin directory](https://claude.com/docs/plugins/org-sync#keep-executables-out-of-the-top-level-bin-directory).
- Each plugin `source` in `marketplace.json` starts with `./`. Claude Code also accepts a bare name under `metadata.pluginRoot`, but the sync rejects it. See [Plugin sources that organization sync accepts](https://claude.com/docs/plugins/org-sync#plugin-sources-that-organization-sync-accepts).
- The `name` in each `plugin.json` is kebab-case: lowercase letters, digits, and hyphens. The sync requires that form. See [Marketplace validation errors](https://code.claude.com/docs/en/plugins/troubleshooting#marketplace-validation-errors).
- The owner adds the marketplace with "Add marketplace", and that way takes a public GitHub repository. See [Find and add a plugin](https://claude.com/docs/plugins/overview#find-and-add-a-plugin). The organization sync of a Team or Enterprise plan is a different way: it needs a private or internal repository on github.com. See [Plugin sources that organization sync accepts](https://claude.com/docs/plugins/org-sync#plugin-sources-that-organization-sync-accepts).

To add a key to `plugin.json` or `marketplace.json`, add it to the key lists at the top of `tests/test_claude_ai_sync.py` in the same PR. Name the new key in the PR description, so that the owner reads the sync result after the merge. The result is in claude.ai. Open Settings, then Customize, then Plugins, and select "Manage marketplaces". The entry of the marketplace shows the sync state, the synced commit, and each notice. If a sync shows a warning that no test knew, open an issue with the exact text of the warning. The PR that fixes it adds a test for the rule and a line to this list.

The sync page can also show this notice for a plugin:

```text
Executable files or settings may differ from the version you were using before this sync.
```

The docs do not say what starts it. It is not a warning, and no test checks it. Three sync results are on record:

| Sync | Plugin | Changed files of the plugin | Notice |
| --- | --- | --- | --- |
| release 4.11.1 | dev-essentials | the version in `plugin.json`, and one Python script of a skill | yes |
| release 4.11.1 | kb | the version in `plugin.json`, and one shell script of a skill | no |
| release 4.11.1 | doc-styles and dotnet-backend-dev | none | no |
| release 4.11.3 | doc-styles and kb | only `plugin.json`: the `icon` key is gone, and the version is new | yes |
| release 4.11.3 | dev-essentials and dotnet-backend-dev | the same change of `plugin.json`. If the sync compares with release 4.11.1, also the eval files and the version of release 4.11.2 | yes |
| release 4.11.4 | doc-styles | the version in `plugin.json`, and `hooks/hooks.json` | yes |
| release 4.11.4 | the three other plugins | none | no |

So a plugin with no change gets no notice. A changed hook file came with a notice, and so did a removed key of `plugin.json`. A new version alone does not explain the notice, because kb got a new version in release 4.11.1 and no notice. A script change alone does not explain it either: the Python script came with a notice, and the shell script did not. The notice tells that a plugin changed. It asks for no fix.

The table does not show which commit a sync compares with. If a sync shows the notice for a plugin with no change, add the result to the table.
