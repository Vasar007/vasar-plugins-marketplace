# vasar-plugins-marketplace

[![Tests](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Vasar007/vasar-plugins-marketplace/actions/workflows/tests.yml) [![Latest release](https://img.shields.io/github/v/release/Vasar007/vasar-plugins-marketplace)](https://github.com/Vasar007/vasar-plugins-marketplace/releases/latest) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE) [![Claude Code plugin marketplace](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-D97757.svg)](https://code.claude.com/docs/en/plugin-marketplaces)

This is a personal [Claude Code](https://code.claude.com/docs/en/overview) marketplace. Its plugins help with everyday development: generic developer workflows with a gated task pipeline, a writing style for technical documents, and a .NET backend toolkit.

> This repository is private. Its artifacts are generic and stack-neutral. They carry no employer or product branding.

## Plugins

| Plugin | Group | Purpose |
|---|---|---|
| [`dev-essentials`](./essentials/dev-essentials) | `essentials` | Cross-stack workflows for everyday development with Claude Code. They help you plan, implement, review, and document changes, and keep git and pull requests in order. |
| [`doc-styles`](./essentials/doc-styles) | `essentials` | A writing style for technical documents. Its skill writes and rewrites docs as Markdown in the style of the OpenBSD manual pages. You must name that style to start it, for example "OpenBSD style" or "like a man page". It sets no style for chat replies. |
| [`dotnet-backend-dev`](./dotnet/dotnet-backend-dev) | `dotnet` | Skills, a command, and an agent for .NET backend services that use Clean Architecture, DDD, and EF Core. They create the usual parts of such a service and its tests, and follow one hub of backend conventions. Most templates assume a private shared framework of guard and wrapper types. |

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
/plugin install doc-styles@vasar-plugins-marketplace
/plugin install dotnet-backend-dev@vasar-plugins-marketplace
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

The background update does not ask for credentials. The repository is private, so the update works only with a stored git credential or with an SSH key in `ssh-agent`. The pages [Keep plugins updated](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated) and [When auto-update runs](https://code.claude.com/docs/en/plugins/loading#when-auto-update-runs) give the details.

## Rules for push, force push, and --no-verify

A skill of this marketplace pushes in three cases: the user says yes, the user passes a push flag such as `--push` or `--commit-push`, or the user passes `--autonomous`. Some skills that push say never to force-push, for example `process-pr-comments` and `feature-pipeline`. Some skills that commit say never to pass `--no-verify`. These rules are text in the skills. A plugin cannot ship permission rules, so the plugins cannot enforce them. To enforce them, add the rules below to your own configuration file, for example `~/.claude/settings.json`. Claude Code evaluates deny rules first, then ask rules, then allow rules, and the first match decides. A deny rule also applies to each part of a compound command (`&&`, `;`, `|`).

```json
{
  "permissions": {
    "deny": [
        "Bash(git push --force*)",
        "Bash(git push * --force*)",
        "Bash(git push -f*)",
        "Bash(git push * -f*)",
        "Bash(git -C * push --force*)",
        "Bash(git -C * push * --force*)",
        "Bash(git -C * push -f*)",
        "Bash(git -C * push * -f*)",
        "Bash(* --no-verify*)",
        "PowerShell(git push --force*)",
        "PowerShell(git push * --force*)",
        "PowerShell(git push -f*)",
        "PowerShell(git push * -f*)",
        "PowerShell(git -C * push --force*)",
        "PowerShell(git -C * push * --force*)",
        "PowerShell(git -C * push -f*)",
        "PowerShell(git -C * push * -f*)",
        "PowerShell(* --no-verify*)"
    ]
  }
}
```

You can also add ask rules for a push. With these rules, Claude Code prompts you for each push. In `dontAsk` mode, it denies the push instead. The prompt appears also in an `--autonomous` run, and also after you said "push". If you want that cost, add them.

```json
{
  "permissions": {
    "ask": [
        "Bash(git push *)",
        "Bash(git -C * push *)",
        "PowerShell(git push *)",
        "PowerShell(git -C * push *)"
    ]
  }
}
```

These rules guard the usual form of a command. They are not a security boundary. A rule matches the command text that Claude writes. It does not match other forms, for example `git -c push.default=current push`, a `+` refspec such as `git push origin +main`, or `git commit -n`. A rule with `*` also blocks a command that only contains the text, for example a commit message that names `--no-verify`. Then write the message to a file, and commit with `git commit -F <file>`. A force push that you want is blocked by the deny rules. Run it in your own terminal. See the [permissions page](https://code.claude.com/docs/en/permissions) of the Claude Code documentation for the rule syntax.

## Authoring reference

Only readers who modify this marketplace or add new plugins need this section. The official documentation describes the files of a marketplace and of a plugin. This section gives only the rules of this repository.

### Folder structure

Each plugin is in the folder `<group>/<plugin>/`, for example `essentials/dev-essentials/`. The manifest of the plugin is `.claude-plugin/plugin.json`. The components are in the default folders `skills/`, `agents/`, and `commands/`. For the default layout of a plugin, see [Standard layout](https://code.claude.com/docs/en/plugins/manifest-reference#standard-layout).

These items at the repository root are not part of a plugin:

- `.claude-plugin/marketplace.json` lists every plugin of the marketplace.
- `.gitattributes` makes GitHub count the `.md` files in the language statistics of the repository.
- `.github/workflows/tests.yml` runs the tests in CI.
- `.markdownlint.jsonc` holds the markdownlint rules for the `.md` files.
- `tests/` holds the tests of the repository.

### Rules for `marketplace.json`

Each plugin has one entry in `.claude-plugin/marketplace.json` with the fields `name`, `source`, and `description`. The `source` path has the form `./<group>/<plugin>`. It must start with `./`. It must point to a folder that contains `.claude-plugin/plugin.json`. Do not set `version` here. The version is only in `plugin.json` (see [Versioning Policy](./CLAUDE.md#versioning-policy)). To remove a plugin, delete its entry and add `"<plugin>": null` to the top-level `renames` map. Do not delete an entry of `renames`, because Claude Code reads the map to move the users of old names. For all fields of the file, see the [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference).

### Rules for `plugin.json`

Keep `plugin.json` to metadata and dependencies: `name`, `version`, `description`, `author`, `repository`, `keywords`, `dependencies`, and `userConfig`. A plugin can use a skill or an agent of another plugin of this marketplace. Then list that plugin in `dependencies` by its bare name, for example `"dependencies": ["dev-essentials"]`. Do not add a version range. A range resolves against release tags of the form `<plugin>--v<version>`, and this repository has no such tags. For the field, see [Plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies). Do not set `$schema`. Claude Code accepts it, but the claude.ai sync strips it and shows a warning. Copy the values of `author` and `repository` from the `plugin.json` of an existing plugin of this marketplace, for example `essentials/dev-essentials/.claude-plugin/plugin.json`. The plugins of this marketplace do not set the fields `skills`, `agents`, or `commands`. Claude Code finds the components in their default folders. For all fields, see the [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference).

### Validating

Before you push changes, run the validator from the repository root:

```text
claude plugin validate .                       # validates marketplace.json
claude plugin validate ./<group>/<plugin>      # validates one plugin and its components
```

Run the second command for each plugin that you changed. The run on the repository root does not read the skill, agent, and command files of the plugins. For the flags and the exit codes, see [`plugin validate`](https://code.claude.com/docs/en/plugins/cli-reference#plugin-validate).

### Testing

The folder `tests/` holds the tests of this repository. It is outside every plugin folder, so Claude Code does not copy it into the plugin cache. The tests need Python 3, Git, and Claude Code (the `claude` command). The markdownlint test also needs Node.js 22 or later, because it runs `markdownlint-cli` through `npx`.

To run all tests, run this command from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The command runs these parts:

- The tests of `check_report.py` (skill `bug-hunt`) and `trim_report.py` (skill `trim-artifacts`).
- The simple-english linter on every tracked `.md` file of the repository. A hit fails the test, unless `tests/simple-english-baseline.json` lists it. Each entry of that file gives the reason for the exception. A baseline entry without a hit also fails the test. The `excluded` key of that file lists folders that the test skips as a whole, each with a reason. An `excluded` folder with no tracked `.md` file also fails the test.
- markdownlint on every tracked `.md` file of the repository. The rules are in `.markdownlint.jsonc`. Each rule that the file turns off has a comment with the reason.
- `claude plugin validate --strict` on the marketplace and on each plugin.
- A budget for the always-on cost of each plugin, from `claude plugin details`. The always-on cost is the number of tokens that the names and descriptions of the skills, agents, and commands add to every session. The budgets are in `tests/test_plugin_cli.py`.
- A search of the plugin files for lines that ask the model to write out its reasoning. Such a line can make a model refuse the task.
- The tests of `tests/evals/compare_versions.py`. They use the result file in `tests/evals/fixtures/` and call no model.
- The static checks of every eval case in `tests/test_eval_cases.py`. They read the cases and call no model.
- The scaffold tests in `tests/test_eval_scaffolds.py`. They run each `scaffold.sh` of the eval cases in a temporary folder. They need Bash and Git. One test also builds a .NET solution, so it needs the .NET SDK 10. If a tool is missing, the test skips. In CI, it fails.
- A version check for each plugin with a changed file. The `version` in its `plugin.json` must be higher than on the base branch.

The two linters read only the files that git tracks. If you add a new `.md` file, run `git add` on it before you run the tests.

The simple-english test first looks for the linter in the folder that the variable `SIMPLE_ENGLISH_DIR` names. This is the root of a clone of SimpleEnglish. Then it looks in the plugin cache. If no linter is found, the test skips. The baseline is for simple-english 2.1.1, so another version can report other hits.

The tests of `claude plugin validate` and `claude plugin details` give each call an empty, temporary configuration folder. So these tests need no sign-in, and they do not load your installed plugins. If the `claude` command is not found, these tests skip.

The version check compares the work tree with the merge base of `HEAD` and a base branch. In a CI run for a pull request, the base branch is the target branch of the pull request. On your machine, it is `origin/main`, or the branch that the variable `VERSION_BUMP_BASE` names. A CI run for a push to `main` skips the check, because the pull request already ran it.

The workflow `.github/workflows/tests.yml` runs the same command on each pull request and on each push to `main`. In CI, a missing linter or a missing `claude` command fails the run. CI installs the latest Claude Code with npm. CI also installs the .NET SDK 10 for the scaffold tests. CI also fetches the full history of the repository, so that the version check finds the merge base. CI uses the latest release of SimpleEnglish, so the linter version does not fall behind. If a new linter version makes the lint test fail, treat it as a blocker. Open an issue and fix it at once.

### Evals

An eval case is a prompt and its graders. A grader is a pass or fail check of a run. `claude plugin eval` runs the cases of a plugin and scores them. Each run calls a model on your account, so CI does not run the evals. The docs page [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) describes the case format.

The script `tests/evals/compare_versions.py` runs one suite on the plugin at a base commit and at a head commit. Then it compares the scores. Both sides run the cases of the head commit. This example runs the suite of `dev-essentials`:

```bash
python3 tests/evals/compare_versions.py run --plugin essentials/dev-essentials --base main --head HEAD --model <model id> --judge-model <model id> --out <folder>
```

Pass full model ids. The result files store them, because a comparison is valid only on the same models. The script writes `base.json`, `head.json`, and `report.md` into the `--out` folder. If the folder already holds a result file, the script stops. For a case that the report marks as unclear, the report prints the commands to run the case again and to compare all result files. To compare result files that you already have, use `compare --base <files> --head <files>`. For the rules of the verdict, run the script with `--help`.

A plugin with dependencies must run through this script. `claude plugin eval` loads only the plugin under test, so the plain command cannot load a dependency. The plugin then reports `dependency-unsatisfied` and does not load. The script copies each plugin that the manifest lists in `dependencies` from the marketplace at the same commit into `.deps/<name>` of the plugin copy. A case lists these copies in the `plugins` field of its `prompt.md`, for example `plugins: ["../../..", "../../../.deps/dev-essentials"]`. The trigger cases of `dotnet-backend-dev` do this, so they load only through the script.

To copy a plugin that the manifest does not list, pass `--extra-dep <name>` to `run` or `baseline` (repeat it for more plugins). The script copies it the same way, and a case lists it in `plugins`. The trigger cases of `doc-styles` use this for `dev-essentials`, because `doc-styles` must stay free of dependencies. The test `tests/test_eval_cases.py` accepts such a copy only for a plugin in `EVAL_ONLY_DEPS`. `baseline` also takes `--ablation none|with-without` (default `none`) and `--keep-temp`.

To record the result of one commit with no comparison, use `baseline`. It runs the suite at one commit with the same copy logic and writes `baseline.json` into the `--out` folder. If this file already exists, the script stops. This example records the trigger cases of `dotnet-backend-dev`:

```bash
python3 tests/evals/compare_versions.py baseline --plugin dotnet/dotnet-backend-dev --commit main --model <model id> --judge-model <model id> --tag triggers --out <folder>
```

Later, pass the file to `compare --base` or `compare --head`. `baseline` runs the cases of its own commit, but `run` runs the cases of the head on both sides. If two commits have different cases, do not compare their baseline files. If an eval fails or writes no case, `baseline` stops with exit code 2.

The trigger cases are in `evals/triggers/` of each plugin. In this section, a unit is a skill, an agent, or a command. Some units have the same trigger words in their descriptions. For each such pair, one case checks that the right unit starts. A near-miss case checks that the unit does not start for the words of the other unit. If another unit owns those words, the case also checks that this other unit starts. A grader with the name `<unit>-not-fired` checks that another unit did not start. The trigger cases use no shell tool, so they also run on native Windows. To run the trigger cases of a plugin without dependencies, run this command from the repository root:

```bash
claude plugin eval essentials/dev-essentials --ablation none --trust-plugin --no-publish --model <model id> --judge-model <model id> --tag triggers
```

To compare only the trigger cases at two commits, add `--tag triggers` to the command of the compare script. The run writes its results into `evals/results/` of the plugin. Git ignores this folder. A suite that grants `Bash` needs the sandbox of Claude Code, and native Windows has no sandbox. Run such a suite under WSL2.

#### Behavior suites

A behavior suite is a set of eval cases that runs a workflow skill on a small planted repository. The graders check the result: the files, the commits, the pushes, and what the final message tells the user. Each suite is in `evals/` of its plugin, and the tag of its cases is the name of the suite.

| Suite | Plugin | Cases | Where it runs |
| --- | --- | ---: | --- |
| `review-loop` | `dev-essentials` | 5 | WSL |
| `subagent-orchestration` | `dev-essentials` | 4 | WSL |
| `process-pr-comments` | `dev-essentials` | 3 | WSL |
| `bug-hunt` | `dev-essentials` | 2 | WSL |
| `create-html-artifact` | `dev-essentials` | 2 | Windows, because it grants no shell tool |
| `feature-pipeline` | `dev-essentials` | 9 | WSL |
| `write-tests` | `dotnet-backend-dev` | 2 | WSL |
| `style-compare-openbsd` | `doc-styles` | 9 | Windows, because it grants no shell tool |
| `style-compare-se` | `doc-styles` | 9 | Windows, because it grants no shell tool |
| `style-compare-both` | `doc-styles` | 3 | Windows, because it grants no shell tool |

The count is the number of behavior cases. If a skill has trigger cases, the tag of its suite also selects them. So `--tag review-loop` runs 7 cases, `--tag feature-pipeline` runs 13 cases, and `--tag write-tests` runs 4 cases.

The `style-compare-*` suites compare the style of `doc-styles` with `simple-english`. The tag `style-compare` selects all 21 cases. The suite `style-compare-openbsd` runs the skill on 9 documents. The suite `style-compare-se` runs the same 9 prompts with `simple-english`. The suite `style-compare-both` runs 3 documents with both plugins loaded. The `simple-english` side loads the stand-in in `essentials/doc-styles/eval-stubs/simple-english`, a byte copy of simple-english 2.1.1. If a newer simple-english is installed, a test fails, so that the copy does not fall behind in silence. The 5 trigger cases of `doc-styles` carry the tag `openbsd-style-docs`, and its 3 probes carry the tag `probe`.

Run the suites through the compare script, because the cases of `dotnet-backend-dev` load `dev-essentials` from a `.deps` copy. A suite that grants `Bash` needs the sandbox of Claude Code, so run it in WSL2. Prepare WSL2 first:

1. Install `bubblewrap` and `socat`. The sandbox needs both.
2. For the `feature-pipeline` and `write-tests` suites, install the .NET SDK 10 outside your home folder. The sandbox cannot read your home folder, so an SDK in `~/.dotnet` does not work. On Ubuntu 26.04, the package `dotnet-sdk-10.0` works.
3. Set `TMPDIR` to a folder outside `/tmp`, `/var/tmp`, `/dev/shm`, and `/run/shm`, and make that folder. The sandbox of a run denies these four folders, and the run folder follows `TMPDIR`. If `TMPDIR` points to one of them, no Bash write works in the run. This is a bug of Claude Code ([anthropics/claude-code#104631](https://github.com/anthropics/claude-code/issues/104631)). The `run` and `baseline` commands stop with a message in this case.

This example runs the `review-loop` suite in WSL2. Pass `--scaffold`, because each case builds its repository with its `scaffold.sh`. Pass `--allow-tools`, because a run asks for no permission and grants no shell tool by default. If the shell does not find `claude`, pass its path with `--claude`.

```bash
export TMPDIR=$HOME/.cache/plugin-evals/tmp
mkdir -p "$TMPDIR"
python3 tests/evals/compare_versions.py baseline --plugin essentials/dev-essentials --commit <branch> --model <model id> --judge-model <model id> --scaffold --runs 3 --concurrency 3 --max-cost-usd <usd> --tag review-loop --out <folder> --allow-tools Bash Write Edit
```

A `scaffold.sh` script builds the repository of a case. It sources the functions in `evals/_lib/` of its plugin. The repository has a bare remote in `.remote/origin.git`, and each fixture commit has a subject that starts with `fixture:`. The cases with `mocks` answer the calls to the GitHub tools with mock files. They load the stand-in plugin in `essentials/dev-essentials/eval-stubs/github`, which declares the name of the server. The stand-in is outside `evals/`, because `claude plugin eval` refuses a plugin that sits in the eval folder of the case.

The .NET cases need `-m:1`. The sandbox blocks the Unix sockets that the worker nodes of MSBuild need, so a plain `dotnet build` or `dotnet test` of a solution fails. With `-m:1`, MSBuild builds in one process, and the build works. So the prompt of each .NET case tells the agent to pass `-m:1`. The grader `route-plain-dotnet` counts the plain calls. A run has no network. The scaffold of a .NET case restores the packages into the shared folder `/tmp/plugin-evals/nuget`. Then it copies them into the home folder of the run, because the run cannot read `/tmp`.

The probes are cheap cases that test the run environment, not a skill. They are in `evals/probes/` of each plugin, and the tag is `probe`. Run them with the same command and `--tag probe` before the first paid suite run on a new machine.

Do not commit baseline files. A result file holds local temporary paths, so keep the baselines outside git.

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
