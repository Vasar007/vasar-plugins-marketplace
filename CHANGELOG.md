# Changelog

This file records all notable changes to this marketplace.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for each plugin separately.
For the current version of a plugin, see the `plugin.json` file of that plugin.
In each release heading, the linked number is the release tag of the marketplace, for example `v2.1.0`.
The other numbers in a heading are plugin versions.

## [Unreleased]

## kb 0.2.0 in release [4.2.0] - 2026-10-29

This release lets KB sessions run the two text checks and read-only git in the KB with no prompt. It also adds plain allow rules as a fallback.

### Added in kb

- `hooks/hooks.json`: a second `PreToolUse` group with the matcher `Bash`. It calls the `allow-read` script of the KB clone, which approves the two text checks and read-only git in the KB. If the clone has no such script, the launcher exits 0 (issue #91).

### Changed in kb

- `skills/setup/check.sh`: it checks the allow rules for the two text checks, the three `git -C <KB root>` allow rules (`status`, `log`, `show`), and the ask rule for `--output`. It reads the `allow` and `ask` lists separately and matches whole entries. On Windows, it accepts the path rule with the drive letter in upper case or in lower case (issue #91).
- `.claude-plugin/plugin.json`: the description names the approval of read-only commands (issue #91).
- `skills/setup/SKILL.md`: step 2 names where the rules go and bans a rule for a git command that changes the KB (issue #91).
- `README.md`: the hook table, the setup pieces, and a limit for a KB clone with no `allow-read` script, and a limit that explains why there is no plain `git diff` rule (issue #91).

### Changed in the repository

- `README.md`: the `kb` row names the approval of read-only commands (issue #91).
- `tests/test_kb_plugin.py`: tests for the `allow-read` hook entry, the launcher, and the new rule checks (issue #91).

## dev-essentials 3.7.1 and doc-styles 1.0.1 in release [4.1.1] - 2026-10-28

This release moves the eval stand-in plugins out of the plugin folders. The claude.ai sync skipped `dev-essentials` and `doc-styles`, because each held a second `.claude-plugin/plugin.json` below its root. No skill, agent, or command changes.

### Fixed in dev-essentials

- `eval-stubs/github`: the stand-in for the GitHub server moved to `tests/evals/stubs/github`. The claude.ai sync skipped the plugin from 3.4.2 on, because the stand-in had its own manifest. The cases that load it now run only through `tests/evals/compare_versions.py`.

### Fixed in doc-styles

- `eval-stubs/simple-english`: the stand-in moved to `tests/evals/stubs/simple-english` for the same reason. The claude.ai sync did not sync 1.0.0.

### Changed in the repository

- `tests/evals/compare_versions.py`: `run` and `baseline` copy each folder of `tests/evals/stubs/` into `eval-stubs/` of the plugin copy. A `run` uses the stand-ins of the head on both sides. `tests/evals/test_compare_versions.py` tests the copy.
- `tests/test_claude_ai_sync.py`: if a tracked file of a plugin is in a `.claude-plugin` folder below the plugin root, a new test fails.
- `tests/test_eval_cases.py`: if `tests/evals/stubs/<name>` is a plugin folder, a `plugins` entry `eval-stubs/<name>` is valid.
- `tests/test_eval_stubs.py`, `tests/support.py`, `.gitignore`, and `README.md`: the new path of the stand-ins.

## kb 0.1.0 in release [4.1.0] - 2026-10-28

This release adds the plugin `kb`. It wires Claude Code to a personal knowledge base that lives in a git repository. No other plugin changes its version.

### Added in kb

- `kb`: a thin plugin that wires Claude Code to a personal knowledge base in git. Five hooks call the launcher `scripts/kb-hook.sh`, which runs the hook scripts of the local KB clone. The hooks are `SessionStart`, `SubagentStart`, `PreToolUse`, `Stop`, and `SessionEnd`. The skills `capture` and `close-task` point to the procedures in the KB. The skill `setup` runs `check.sh`, which changes nothing and prints the OS and one line for each missing piece. The plugin needs a KB clone. If the hooks find none, they exit 0.

### Changed in the repository

- `tests/test_kb_plugin.py`: unit tests for the launcher `kb-hook.sh`. They cover no clone, `KB_DIR`, a clone in a child folder, stdin, and the exit code of the guard. Other tests cover `check.sh` (always exit 0, one line for each missing piece) and the five hook entries.
- `README.md`, `.claude-plugin/marketplace.json`, and `tests/test_plugin_cli.py`: the new plugin has a row in the plugin matrix and an install line. It also has an entry in the marketplace and an entry of 120 tokens in `LISTING_BUDGET`.
- `.gitattributes`: `*.json` files keep LF on Windows, like `*.sh` files, so that a commit from a Windows PC stores LF.

## gop-pipeline removed in release [4.0.0] - 2026-10-28

This release removes the `gop-pipeline` plugin (issue #71). The `feature-pipeline` skill in `dev-essentials` does the same job. The release is MAJOR because an install path goes away: `/plugin install gop-pipeline@vasar-plugins-marketplace` no longer works. No other plugin changes its version.

### Removed

- `gop-pipeline` (issue #71): the plugin, with the `gop-work` skill, its eight agents, and its eval suite. `feature-pipeline` in `dev-essentials` does the same job. To start it, ask Claude to "run the feature pipeline on this request", or run `/dev-essentials:feature-pipeline "<request>"`. The flags `--interactive` and `--autonomous` work as before. One difference: `feature-pipeline` works in a new worktree and ends with a pull request. To work on the current branch, as `gop-work` did, pass `--no-worktree`. The five validators are now the checks of the review and the security review. After `/plugin marketplace update vasar-plugins-marketplace`, Claude Code shows "Removed from the "vasar-plugins-marketplace" marketplace" and turns the plugin off.

### Changed in the repository

- `marketplace.json` (issue #71): the `renames` map records the removal. The description no longer names a separate pipeline plugin.
- `README.md` (issue #71): the plugin table, the install lines, and the eval notes no longer name `gop-pipeline`.
- The tests (issue #71): they no longer name the `gop-` cases or the `gop-pipeline` folder.

## dev-essentials 3.7.0 in release [3.10.0] - 2026-10-28

This release lets `feature-pipeline` take over the useful parts of `gop-work` (issue #71). So `gop-pipeline` can go in the next release. The pipeline takes a plain request. Its review has new lenses, and a new supply-chain check. It keeps the changes that you made before the run out of its commits. A new eval suite measures it.

### Added in dev-essentials

- `feature-pipeline` (issue #71): If the user names the pipeline, Claude can start it (`when_to_use`). A small edit does not start it. `implement-task`, `implement-batch`, and `research-implement-review-report` keep their own requests.
- `feature-pipeline` (issue #71): a plain request as the task, for example `/dev-essentials:feature-pipeline "add a cache to GetQuantity"`. A task with a space is a request. If the project context has no Task Provider, any task is a request. A request run needs no task provider and posts no task comments.
- `feature-pipeline` (issue #71): the request ID. The run gets the ID `req-<slug>`. If a folder or a branch of that ID exists, the run adds `-2`, `-3`, and so on. To resume a request run, pass its `req-<slug>` ID as the task.
- `feature-pipeline` review (issue #71): the performance, reuse, and compliance lenses, and a check of the callers of the changed code. Each finding names its lens. A finding can carry a `Fix:` line.
- `feature-pipeline` security review (issue #71): a supply-chain category. It covers new dependencies, likely typosquats, install scripts of third-party packages, and floating versions. A new dependency is a LOW warning. A likely typosquat is HIGH.
- `feature-pipeline` references (issue #71): `stage-launch.md`, `pipeline-discipline.md`, and `task-comments.md`. The text moved out of `SKILL.md`, which is now shorter.

### Changed in dev-essentials

- `feature-pipeline` (issue #71): behavior change: Stage 7 runs as a `general-purpose` agent with the review method of the skill. The run no longer needs the `feature-dev` plugin.
- `feature-pipeline` (issue #71): behavior change: the review and the security review read one fixed patch, `review-diff.patch`. The master agent writes it. The patch leaves out the paths that you changed before the run. The review runs no git command that changes state. A dependency manifest of a test project is now in the scope of the security review.
- `feature-pipeline` (issue #71): behavior change: the run records the changes in the tree at the start (`startChanges` in the state file). No commit takes them, unless a stage edits that file. The final report lists each path that the run left out under "Not committed".
- `feature-pipeline` (issue #71): behavior change: each commit names its paths after `--`. A rename lists the old path and the new path. A change that you staged before the run stays staged and out of the commit. No stage adds an ignored file, also not with `git add -f`.
- `feature-pipeline` (issue #71): behavior change: with `--no-worktree` on the default branch, on the base branch, or on a detached HEAD, the run stops. It asks for a branch name or for an explicit yes. With `--autonomous`, it creates the branch. With `--dry-run`, it only reports.
- `feature-pipeline` (issue #71): the state file has two new keys, `taskSource` and `startChanges`. A state file of an older run without them resumes with the values `"provider"` and `[]`.
- `implement-task`, `implement-batch`, and `research-implement-review-report` (issue #71): the line that describes `feature-pipeline` now says that the task can be a plain request.
- `promote-conventions` (issue #71): its example of skill frontmatter fields says that `feature-pipeline` sets `argument-hint` and `when_to_use`. It no longer says `disable-model-invocation`.

### Changed in the repository

- The `feature-pipeline` eval suite (issue #71): 9 behavior cases (`fp-*`) and 4 trigger cases, in `essentials/dev-essentials/evals/feature-pipeline` and `evals/triggers`. The fixtures `dotnet-fixture.sh`, `inventory-fixture.sh`, and `pipeline-fixture.sh` are in `evals/_lib/`. The probe `probe-dotnet-sandbox` checks the .NET sandbox. The cases `implement-task-fires` and `implement-task-near-miss` also make sure that `feature-pipeline` does not start. The suite row and the `--tag feature-pipeline` count (13 cases) are in `README.md`.
- Tests (issue #71): `FeaturePipelineGraderTests` has 7 tests for the grader patterns of the suite. The scaffold tests cover the 9 new cases and the `pipeline-fixture.sh` file.

## doc-styles 1.0.0 in release [3.9.0] - 2026-10-28

This release adds the plugin `doc-styles` with the skill `openbsd-style-docs` (issue #73). The skill comes from a public source, and it is adapted for this marketplace. It owns the docs that the user asks for in the style of the OpenBSD manual pages. `simple-english` stays the default for other text and for chat replies.

### Added in doc-styles

- `openbsd-style-docs` (issue #73): writes and rewrites a technical document in the style of the OpenBSD manual pages, as Markdown. The user must name the style to start it. The names are "OpenBSD style", "like a man page", "man-page style", and "BSD style". The document has uppercase sections in a fixed order, a one-line NAME summary, sorted option and error lists, and each default as its own sentence. The chat reply follows the reply rules of the session.
- Eval suites (issue #73): 5 trigger cases, 3 probes, and 21 style-comparison cases. The comparison runs each case with the skill, with `simple-english`, and with both plugins loaded. The OpenBSD docs prompts also name the style.
- `eval-stubs/simple-english` (issue #73): a stand-in for `simple-english` that is used only in the eval runs. It is a byte copy of simple-english 2.1.1 (MIT). If a newer simple-english is installed, the test `tests/test_eval_stubs.py` fails.

### Changed in the repository

- `tests/evals/compare_versions.py` (issue #73): the new option `--extra-dep NAME` copies a plugin of the repository into the `.deps` folder of the bundle for a suite that needs it. `baseline` gets the options `--ablation` and `--keep-temp`. `tests/evals/test_compare_versions.py` tests the changes.
- `tests/test_eval_cases.py` (issue #73): the list `EVAL_ONLY_DEPS` names the plugins that a suite can copy with `--extra-dep`. A new test checks that the two arms of a style comparison differ only in the style.
- `tests/test_simple_english.py` and `tests/simple-english-baseline.json` (issue #73): the simple-english lint test can exclude a folder, with a reason for each folder. The skill `openbsd-style-docs` keeps its own style, so the test excludes its folder. The test also skips the stand-in copy of simple-english.
- `README.md` and `.claude-plugin/marketplace.json` (issue #73): the new plugin has a row in the plugin matrix, an install line, and an entry in the marketplace. The Evals section lists the new suites and the option `--extra-dep`.

## dotnet-backend-dev 1.7.0 and dev-essentials 3.6.0 in release [3.8.0] - 2026-10-27

This release makes seven large dotnet skills shorter. They move examples and rare sections into reference and example files. The skills that write code or Markdown now run a build or a lint loop until it passes (issue #78). Each loop stops after three failed fix attempts, or for an error outside the changed code. The moves keep the rules.

### Added in dotnet-backend-dev

- `create-domain-model`, `create-primitive-wrapper`, `create-exception`, `handle-sensitive-data`, `model-mapping`, `create-controller`, `update-swagger-spec`, `create-external-client`, `add-configuration-option`, `add-session-logging`, and `create-string-resource` (issue #78): a build loop. Behavior change: the skill builds the changed projects with `dotnet build`, fixes the errors, and reports the result line of the last build. The skills with a code generator do not edit a generated file, and they point to their stop-and-ask rule. For an error that names a missing generated member, they do not change the calling code. `model-mapping` also fixes each unmapped member that the build reports. `update-swagger-spec` runs the loop as a new last step.
- `add-migration` (issue #78): a build and migration-test loop on the framework path. The standard EF Core path already had its build.

### Changed in dotnet-backend-dev

- `add-migration` (issue #78): the framework text moved to `references/framework-migrations.md` and `references/cosmos-db.md`. The hard rules stay in `SKILL.md`.
- `update-swagger-spec` (issue #78): the common spec patterns moved to `references/common-patterns.md`. Step 1 now states the `500` rule and its reason.
- `create-tests` (issue #78): the helper and mocking examples moved to `examples/helper-methods.md` and `examples/mocking-rules.md`, and the checklist comes first. The forbidden list for scenario tests points to the table of `examples/scenario-tests.md`. The builder rule moved to `examples/mocking-rules.md`.
- `model-mapping` (issue #78): the full examples moved to `examples/full-examples.md`.
- `add-configuration-option` (issue #78): the `BuildEnvironment` pattern moved to `references/build-environment.md`.
- `handle-sensitive-data` (issue #78): the JSON converter code moved to `references/serialized-output.md`.
- `add-session-logging` (issue #78): the two Best Practices sections are one section.

### Changed in dev-essentials

- `write-markdown` (issue #78): the validation workflow loops on `markdownlint` until the exit code is `0`. An exit code of `2` to `4` is a configuration error, and the skill reports it. Usage text from `markdownlint` means that the path matched no file.
- `create-documentation` (issue #78): the checklist starts with a `markdownlint` loop until exit `0`. The list keeps the four items that the linter cannot test: the file name, the title heading, the contents list, and the relative links. Usage text from `markdownlint` means that the path matched no file.
- `generate-xml-docs` (issue #78): a CS1591 build loop with `-p:GenerateDocumentationFile=true` for that build only. The checklist stays the test for internal members. If the project hides CS1591 or sets `TreatWarningsAsErrors`, the skill names the fallback.

## dev-essentials 3.5.0 and dotnet-backend-dev 1.6.5 in release [3.7.0] - 2026-10-27

This release gives each trigger phrase one owner. It puts the hard rules and the done test of the large dev-essentials skills first. It turns two commands into skills with the same names, and it splits the promotion out of `audit-personal-conventions`. It also adds two plugin options (issue #76). The two moved units keep their invocation paths. Every `/dev-essentials:research-implement-review-report` and `/dev-essentials:implement-batch` call works as before.

### Added in dev-essentials

- `promote-conventions` (issue #76): Phases 5 to 10 of the old audit. Only the user starts it, with `/dev-essentials:promote-conventions`, because the skill sets `disable-model-invocation: true`. Per the skills docs, its description is not in the skill listing.
- `userConfig` options (issue #76), set with `/plugin configure dev-essentials@<marketplace>`:
  - `branch_prefix`, default empty: the first segment of the task branches. The order of the rules is the flag. Then come the `CLAUDE.md` of the repo, this value, and the `CLAUDE.md` of the user. Last comes one question to the user.
  - `notes_dir`, default `Notes`: the folder for plans, reports, reviews, and progress files. A location that the repo documents wins.
  - A value that is not saved stays a `${user_config...}` placeholder in the text. Each skill and command reads that as an empty prefix and as the folder `Notes`. So a user who sets nothing sees the old behavior.
- Reference files (issue #76): review-loop `parameters.md` and `output-formats.md`, process-pr-comments `parameters.md` and `invocation-examples.md`, and subagent-orchestration `model-selection.md`.
- Trigger cases `audit-personal-conventions-fires` and `promote-conventions-near-miss`, and the listing probes `probe-listing` (issue #76).

### Changed in dev-essentials

- `audit-personal-conventions` (issue #76): behavior change: every triage that stops ends with the command `/dev-essentials:promote-conventions`. These flags moved to that skill: `--resume`, `--cross-repo`, `--delete-personal-entities`, `--update-global-claude-md`, `--cleanup-mode`, `--rounds`, `--report`, `--interactive`, and `--autonomous`. They still work on the audit. A reply such as `approve 1,3` works too. The audit reads `promote-conventions` and continues into its Phase 5 in the same run in these cases only: a promote request, with or without a flag of the promotion, and `--resume`. A question or an audit stops after the triage, also with a flag of the promotion, `--autonomous`, or `--interactive`. `--dry-run` always stops after the triage. So an old invocation keeps its path, and the bump stays MINOR.
- `research-implement-review-report` and `implement-batch` (issue #76): now skills with the same names, so every invocation works as before.
- `general-conventions` (issue #76): PowerShell only. Its frontmatter rules moved to `write-markdown`.
- `write-markdown` (issue #76): the general markdownlint examples, the file template, and the quick reference are cut. The skill keeps the two choices that are not linter defaults.
- review-loop, process-pr-comments, and subagent-orchestration (issue #76): the rules and the done test come first, and the parameters, the examples, and the model detail moved to reference files. review-loop and process-pr-comments got a done test, and review-loop got one new hard rule (the head gate before the first fix).
- `task-composer`, `compose-pr`, `create-html-artifact`, and `general-conventions` (issue #76): trigger words, so that each phrase has one owner.
- `git-worktree-management`, `help-review-pr`, `implement`, `implement-task`, `opsx-implement`, `save-context`, `research-implement-review-report`, `implement-batch`, and `review-loop` (issue #76): they read the notes folder from the new option. `research-implement-review-report`, `implement-batch`, `implement-task`, and `promote-conventions` also read the branch prefix. Examples with a path keep `Notes/`.

### Fixed in dev-essentials

- `review-loop` (issue #76): the final chat message now always holds the `Stop verdict:` line and the path of each fixed file. Before, a run with the summary in a file or with a report format of the user often left it out.

### Changed in dotnet-backend-dev

- `create-ef-entity`, `model-mapping`, `create-tests`, and `/write-tests` (issue #76): one owner for "EF mapping" and for one test in an existing class.

### Changed in the repository

- `README.md` (issue #76): `userConfig` in the list of `plugin.json` fields.

## dev-essentials 3.4.4 and dotnet-backend-dev 1.6.4 in release [3.6.5] - 2026-10-27

This release changes the text of skills, commands, and agents (issue #74). Each workflow states its own gates. Plain rules replace shouted words. Long reference files get a contents list. Two plugins name what they assume. The old shared block and the steps of some workflows disagreed. In these cases the table keeps what the step says. The `bug-hunt` cleanup deletes the paths that the run made with no stop. A few gates, such as the report path of `audit-personal-conventions` and the reference conflict of `implement-task`, still ask in the default mode.

### Changed in dev-essentials

- 14 workflows (issue #74): the "Autonomy" section lists the gates of the workflow in a table, in place of a block that 14 files shared. Six are commands: `implement`, `opsx-implement`, `research-implement-review-report`, `implement-task`, `implement-batch`, and `save-context`. Eight are skills: `audit-personal-conventions`, `bug-hunt`, `feature-pipeline`, `git-worktree-management`, `optimize-skill`, `process-pr-comments`, `review-loop`, and `trim-artifacts`.
- Plain rules in place of shouted words (issue #74): 47 files.
- Contents lists (issue #74): 31 reference and example files. `bug-hunt` links `references/report-format.md`, and `optimize-skill` links `examples/bug-hunt-audit.md`.
- `opsx-implement` names the `openspec` CLI, and `audit-openspec` names the OpenSpec folder layout. `generate-xml-docs` names its guard style (issue #74).

### Changed in dotnet-backend-dev

- Plain rules in place of shouted words (issue #74): 30 files.
- Contents lists (issue #74): 21 reference and example files.
- The templates name the private shared framework (issue #74). The `dotnet-conventions` hub has a paragraph about it, nine skills have a dependency line, and the plugin description has one sentence about it.

### Changed in the repository

- `README.md` (issue #74): a new section with permission rules for push, force push, and `--no-verify`. The dotnet-backend-dev row names the shared framework.
- `.claude-plugin/marketplace.json` (issue #74): the same description change.
- `CLAUDE.md` (issue #74): a new section with the workflow for new and imported units.
- `tests/simple-english-baseline.json` (issue #74): five entries for heading words that the new contents lists repeat.

## dev-essentials 3.4.3 in release [3.6.4] - 2026-10-27

This release changes the reviewer prompts (issue #72). Reviewers now report every finding with a severity and a confidence, and one later step filters them. Blanket second passes and persona lines are gone. Where a change alters behavior, the bullet says so.

### Changed in dev-essentials

- `review-loop` (issue #72): behavior change: the reviewer brief asks for every finding with a severity, a confidence, and a failure case. Phase 4 is the only filter, and it defers a Low or Nit finding unless the reviewer puts it under Must fix before merge. The finding counts are now a signal for the triage, and the run no longer asks for a stricter second review. The reviewer prompts of the branch, pr, last-commits, and diff-range briefs open with the goal, not a persona.
- `review-loop` (issue #72): behavior change: the large-target mode has no Finding Verifier subagent and has three roles. In the synthesis, the main agent reads the lines of each finding and makes sure that the diagnosis matches them. An Area Explorer reports every finding with a confidence, and the word cap on the whole reply is gone. Each field keeps its own limit.
- `help-review-pr` (issue #72): behavior change: the review reports every finding with a severity, and the findings table is sorted by severity. So `--mode=post-all` now posts a comment for every finding, also the Nits, and it can post more comments than before. The mode `--orchestrate` has no Finding Verifier.
- `audit-team` (issue #72): behavior change: each role reports every issue with a confidence, and the consolidation is the only filter. The Reverify step is gone. The role prompt names a point of view, not a persona.
- `audit-plan` and `audit-openspec` (issue #72): the Reverify step is now a step that makes sure that each cited `path:line` says what the finding claims.
- `feature-pipeline` (issue #72): behavior change: the security stage now reports the LOW findings and the findings below a confidence of 0.8. They go under Warnings, and the human sees them at Human Approve #2. The subtle web vulnerabilities of precedent 5 now follow the same confidence rule, so a HIGH one can still block. The fix round still takes only the Blocking Issues. The code review stage asks for every issue with a confidence. The stage prompts open with the goal, not a persona.
- `engineering-discipline` (issue #72): behavior change: the diff scan runs in the main session in every mode, and the line that asks to re-read the skill is gone.
- `docs-composer` (issue #72): the agent prompt has no persona line, and the style rules have no emoji.

## dev-essentials 3.4.2, dotnet-backend-dev 1.6.3, and gop-pipeline 1.4.3 in release [3.6.3] - 2026-10-26

This release adds behavior suites (issue #69). A behavior suite is a set of eval cases that runs a workflow skill on a small planted repository and grades the result. Each case builds its repository with a `scaffold.sh` script, and the graders check the files, the commits, the pushes, and the final message. CI does not run the suites, because each run calls a model. No skill, agent, or command changes, so the plugins behave as before.

### Added in dev-essentials

- `evals/review-loop/` (issue #69): 5 cases for the `review-loop` skill.
- `evals/subagent-orchestration/` (issue #69): 4 cases for the `subagent-orchestration` skill.
- `evals/process-pr-comments/` (issue #69): 3 cases for the `process-pr-comments` skill. Mock files answer the calls to the GitHub tools.
- `evals/bug-hunt/` (issue #69): 2 cases for the `bug-hunt` skill.
- `evals/create-html-artifact/` (issue #69): 2 cases for the `create-html-artifact` skill. They grant no shell tool, so they also run on native Windows.
- `evals/probes/` (issue #69): 2 probe cases that test the run environment, not a skill: the git sandbox and the GitHub mocks.
- `evals/_lib/` (issue #69): the Bash functions that the scaffold scripts use to build the fixture repositories.
- `eval-stubs/github` (issue #69): a stand-in plugin that declares the GitHub server, so that the mock files can answer for it. It is outside `evals/`, because `claude plugin eval` refuses a plugin in the eval folder.

### Added in dotnet-backend-dev

- `evals/write-tests/` (issue #69): 2 cases for the `write-tests` command.
- `evals/probes/` (issue #69): 1 probe case for the .NET fixture.
- `evals/_lib/` (issue #69): the fixture functions for the Billing solution.

### Added in gop-pipeline

- `evals/gop-work/` (issue #69): 9 cases for the `gop-work` skill, from the scenarios E1 to E6 and E8.
- `evals/probes/` (issue #69): 1 probe case for the .NET fixture.
- `evals/_lib/` (issue #69): the fixture functions for the Inventory solution and a Python repository.

### Changed in the repository

- `tests/evals/compare_versions.py` (issue #69): the new option `--concurrency` sets the number of runs at the same time. If a run grants `Bash` on Linux, the script now checks the temporary folder. If the folder is `/tmp`, `/var/tmp`, `/dev/shm`, `/run/shm`, or under one of them, the script stops with a message. The sandbox of a run denies writes to these folders, so every Bash call in the run fails ([anthropics/claude-code#104631](https://github.com/anthropics/claude-code/issues/104631)). `tests/evals/test_compare_versions.py` tests both changes.
- `tests/test_eval_cases.py` (issue #69): static checks of every eval case. They call no model.
- `tests/test_eval_scaffolds.py` (issue #69): runs each scaffold script in a temporary folder and checks the repository that it builds. One test builds a .NET solution.
- `.github/workflows/tests.yml` (issue #69): CI installs the .NET SDK 10 for the scaffold tests.
- `.gitattributes` (issue #69): shell scripts keep LF line ends on Windows, so that the scaffolds run in Bash.
- `.gitignore` (issue #69): the stand-in plugin keeps its `.mcp.json`.
- `tests/simple-english-baseline.json` (issue #69): three new entries for text that is not prose, with the reason for each.
- `README.md` (issue #69): the Testing section names the new tests. A new section of Evals explains the behavior suites, the WSL2 setup, the `TMPDIR` rule, the `-m:1` option for .NET builds, and the probes.

## dotnet-backend-dev 1.6.2 and gop-pipeline 1.4.2 in release [3.6.2] - 2026-10-25

The trigger cases of dotnet-backend-dev and gop-pipeline tested nothing (issue #67). Both plugins list `dev-essentials` in `dependencies`, and `claude plugin eval` loads only the plugin under test. So the eval session reported `dependency-unsatisfied` and did not load the plugin. A case can now load the dependency. No skill, agent, or command changes, so the plugins behave as before.

### Fixed in dotnet-backend-dev

- `evals/triggers/` (issue #67): each of the 10 trigger cases now sets `plugins: ["../../..", "../../../.deps/dev-essentials"]` in its `prompt.md`. The plugin and its dependency now load in the eval session. The cases load only through `tests/evals/compare_versions.py`, because the `.deps` folder exists only in the copy that the script makes.

### Fixed in gop-pipeline

- `evals/triggers/` (issue #67): the same fix for the 2 trigger cases.

### Changed in the repository

- `tests/evals/compare_versions.py` (issue #67): the script now reads `dependencies` from the manifest of the plugin at each commit. It copies each dependency from the marketplace at the same commit into `.deps/<name>` of the plugin copy. An entry can be a name, `name@marketplace`, or an object with a name. A dependency that is not in the marketplace is an input error. A new `baseline` subcommand runs one suite at one commit and writes one result file with no comparison. It does not overwrite an existing result file.
- `tests/evals/test_compare_versions.py` (issue #67): new tests for the dependency copy and the `baseline` subcommand. They call no model.
- `README.md` (issue #67): the Evals section says that a plugin with dependencies must run through the script, and it shows the `baseline` command.

## dev-essentials 3.4.1, dotnet-backend-dev 1.6.1, and gop-pipeline 1.4.1 in release [3.6.1] - 2026-10-25

This release adds the first eval tooling (issue #65). An eval runs test prompts and scores each run with graders. CI now runs `claude plugin validate` and a budget test for the always-on cost of each plugin. It also searches for lines that ask the model to write out its reasoning, and it checks that each changed plugin raises its version. A new script compares one eval suite at two commits. Each plugin gets trigger cases for the units whose descriptions share trigger words. A unit is a skill, an agent, or a command. No unit changes, so the plugins behave as before.

### Added in dev-essentials

- `evals/triggers/` (issue #65): 18 trigger cases for 9 pairs of units, for example `review-loop` and `help-review-pr`. For each pair, one case checks that the right unit starts. A near-miss case checks that the unit does not start for the words of the other unit. If another unit owns those words, the case also checks that this other unit starts. CI does not run them, because each run calls a model.

### Added in dotnet-backend-dev

- `evals/triggers/` (issue #65): 10 trigger cases for 5 pairs of units, for example `create-controller` and `update-swagger-spec`.

### Added in gop-pipeline

- `evals/triggers/` (issue #65): 2 trigger cases. They check that `gop-work` starts on a request for GOP mode, and not on a plain request to implement and commit a task.

### Added in the repository

- `tests/test_plugin_cli.py` (issue #65): runs `claude plugin validate --strict` on the marketplace and on each plugin. It also compares the always-on cost of each plugin from `claude plugin details` with a budget.
- `tests/test_prompt_phrases.py` (issue #65): fails on a line in a plugin file that asks the model to write out its reasoning. Such a line can make a model refuse the task.
- `tests/evals/compare_versions.py` (issue #65): runs one `claude plugin eval` suite on the plugin at a base commit and at a head commit, or reads two finished result files. It then gives a verdict with the rules of the single-agent-loop-kit. A lower mean score or a missing case fails. A change in at most one run is marked as possible noise, and the report prints the commands to run those cases again. If the output folder already holds a result file, the script stops. The report names the agent model and the judge model of each side, and it shows route checks as information only. `tests/evals/test_compare_versions.py` tests it on a fixture result file and calls no model.
- `tests/test_version_bump.py` (issue #65): if a pull request changes a file of a plugin, and the version of that plugin does not go up, the test fails.

### Changed in the repository

- `.github/workflows/tests.yml` (issue #65): CI installs the latest Claude Code with npm. CI also fetches the full history, so that the version check finds the merge base.
- `.gitignore` (issue #65): git ignores the `evals/results/` folder of each plugin.
- `README.md` (issue #65): the Testing section names the new tests. A new Evals section says how to run the trigger cases and the compare script by hand.

## dotnet-backend-dev 1.6.0 in release [3.6.0] - 2026-10-25

Some instructions of dotnet-backend-dev contradicted another file, or fired on a request that they did not support (issue #62). The `add-migration` skill now has a path for a standard EF Core repo. The templates and the examples now follow the rules of the skills. Some fixes change the code that a skill writes on purpose. Each of these bullets says so.

### Added in dotnet-backend-dev

- `add-migration` (issue #62): the skill fired on "add migration" in any repo, but it taught only the migration interfaces of the framework. In a standard EF Core repo, the code that it wrote did not build. A new first step finds out which migration system the repo uses. A new section adds a standard EF Core migration with `dotnet ef migrations add`, and gives the install command of the `dotnet-ef` tool. The command pins the version of the EF Core packages. A migration can have custom code in its `Up` and `Down` methods, for example a data backfill. The table goes by the production provider. If both systems match, the skill asks the user. Behavior change: in a repo without the framework, the skill runs `dotnet ef` and writes no framework migration class. In a repo with no migration system and a document database, it stops and asks the user.

### Fixed in dotnet-backend-dev

- `add-migration` (issue #62): the steps for a new partition key deleted the old Cosmos DB container with no question to the user. Behavior change: the skill now asks the user before the delete.
- `create-ef-entity` (issue #62): the skill added a `DbSet` and stopped. On a relational provider, the first query then failed, because the table did not exist. Behavior change: a new Step 7 builds the changed projects. If the production provider is relational, it then adds a migration with `add-migration`. If the production provider is not clear, it asks the user.
- `update-swagger-spec` (issue #62): the step for the controller showed a `public sealed` class on `ControllerBase` with no try-catch. This sketch broke the rules of `create-controller`. The sketch is gone, and the step points to `create-controller` for the class.
- `create-tests` (issue #62): the skill ran the full test suite before it reported the work as complete. `dev-essentials:dotnet-build-test` forbids a run with no filter in a repo with integration tests. Behavior change: the skill now runs the test classes that it wrote or changed, with a filter. It runs them in one run with one filter. The full suite runs in two cases only. The user asks for it, or the user says yes to it after a props-file change.
- `add-configuration-option` (issue #62): the template put `[Required]` on two `Int32` properties, where the attribute has no effect. Two range rules used the message for a missing value. Behavior change: the template has no `[Required]` on a value type. Each rule gets a message from the error builder that matches the rule.
- `create-domain-model` (issue #62): the `ToString` rule said to include all fields, against the rule to erase sensitive information. It now says to include all fields, and to write the erased placeholder as the value of each field with sensitive information.
- `create-tests` and `dotnet-conventions` (issue #62): the rule made each test data generator a singleton with a static `Instance` property. This is a rule of the project: a shared static generator caused test failures that were hard to trace in real projects. Behavior change: each test class now creates its generators with `new {Model}Generator()`, and the generator template has no `Instance` property. All examples follow the new rule.
- `create-tests` (issue #62): two examples built the class under test with `Fixture.Create` in the test case, against Gate 3. They now call a `CreateService()` helper. The rule against inline test data now names its one exception: an options record in a configuration test.
- `test-engineer` (issue #62): the description said to use the agent for "write tests for X". So a request for one class can start an agent that cannot ask the user a question. The sentence is gone. The agent serves the `/write-tests` command.

## dev-essentials 3.4.0 in release [3.5.0] - 2026-10-25

This release fixes workflow bugs in dev-essentials (issue #60). Some rules contradicted each other. Some steps made a commit, a push, or a deletion that the user did not ask for. Where a fix changes behavior on purpose, the bullet says so.

### Added in dev-essentials

- `scripts/backup_move.py` (issue #60): a script that moves notes files to a backup folder outside the workspace. It never deletes a file, and it refuses a file that git tracks. Without `--apply`, it prints the plan only. `save-context` uses it.

### Changed in dev-essentials

- `audit-personal-conventions` (issue #60): behavior change: a question or an audit request, such as "which of my rules belong in the marketplace?", now stops after the Phase 4 triage. Before, the default mode approved its own triage, authored the entities, committed them, and bumped a version. Phase 5 and the later phases now run only on a request to promote. A reply to the triage with the Phase 5 verbs is such a request.
- `save-context` (issue #60): behavior change: Step 5 moves the finished notes files to a backup folder outside the workspace with `backup_move.py`. Before, it deleted them with no stop and no copy. `research-implement-review-report` and `implement-task` now say "move" where they said "delete".
- `implement-batch` (issue #60): behavior change: the plan files stay out of every commit. Step 2 makes no commit, and its plan-review loops pass the new `review-loop` option `--no-commit`. The commit of task 1 no longer holds the plans. Before, a repo that ignores the plan folder got an empty plans commit, and other repos shipped the plan files. The final report names the plan paths.
- `implement` (issue #60): behavior change: a commit holds no plan file and no research file. The commit message follows the style of the repo, with no `Phase N: Task X.Y` numbers.
- `opsx-implement` (issue #60): the commit message follows the style of the repo, with no phase or task numbers of `tasks.md`.
- `feature-pipeline` (issue #60): behavior change: the finalization stage makes the commit and returns the facts for the push and the PR. The master agent then pushes and creates the PR in the main session. Before, the stage subagent pushed, against Rule 4 of `subagent-orchestration`.
- `review-loop` (issue #60): new option `--no-commit` for a caller that keeps the target out of commits, for example a plan file. Phase 7 makes no commit, and Phase 8 re-reviews the whole target.
- `review-loop` (issue #60): behavior change: for `target=pr <id>`, Phase 5 compares `HEAD` with the fetched PR head before the first fix. If they differ, the run asks the user, or with `--autonomous` it continues as `--dry-run`. Before, the fixer edited and committed on the branch that was checked out, also on an unrelated branch such as `main`. The trigger phrases now name the loop and its fixes, and a plain PR review points to `help-review-pr`. The gate covers `target=diff <range>` too: it compares `HEAD` with the right side of the range, and a range with `HEAD` on the right side needs no check.

### Fixed in dev-essentials

- `process-pr-comments` (issue #60): the copied Autonomy text said that a post stops in the default mode, but Bucket A1 posts replies with no stop. The skill now states its own gates: a reply and a resolve do not stop, and a push and a new issue do.
- `subagent-orchestration` (issue #60): Rule 1 sent a plain "process PR comments" request to a subagent, which cannot ask the user. The main session now invokes `process-pr-comments`, with `dry-run` for a plan only.
- `create-html-artifact` (issue #60): `references/pitfalls.md` said that a review of 1,000 lines has about 1 major item, which can act as a cap. The renderer now shows every finding that the caller gives.
- `bug-hunter` and `bug-verifier` (issue #60): each agent now says that its read-only `gh` commands are its only GitHub source. The rule to use only the GitHub MCP tools is for the orchestrator and the known-issues collector.
- `dotnet-build-test` and `test-runner` (issue #60): a long test run in a subagent no longer polls with `sleep`. A background subagent waits for the notification that its background command ended. `test-runner` sets `background: true`. Then it runs in the background, also for a caller that waits for it.

### Changed in the repository

- `tests/test_backup_move.py` (issue #60): unit tests for `backup_move.py`.

## gop-pipeline 1.4.0 and dotnet-backend-dev 1.5.0 in release [3.4.0] - 2026-10-25

The GOP pipeline had four bugs and one rule that never applied (issue #58). In some runs, it committed a file that the run did not change, or it committed and pushed on the default branch. A change to a shared build file skipped all tests. A failed build, or a test that failed because of production code, stopped the run. This release fixes them, and each fix changes behavior on purpose. The release also declares `dev-essentials` as a dependency of `dotnet-backend-dev` and `gop-pipeline`, so an install of either plugin also installs it.

### Fixed in gop-pipeline

- `gop-commit` (issue #58): the agent staged every change with `git add -A`. So a commit sometimes took in an untracked file of the user, for example `.env.local`, and `--autonomous` pushed it. Behavior change: `gop-work` now gives the agent the files of the run, and the agent stages and commits only these paths. Changes that the user staged before the run stay staged. The report lists each change that the commit left out.
- `gop-work` (issue #58): no step made a branch, and `gop-commit` must not switch branches. So a run on the default branch committed there, and `--autonomous` pushed to the default branch of the remote. Behavior change: if the run starts on the default branch, Phase 0 stops and asks for a branch name or an explicit yes. With `--autonomous`, Phase 0 creates a branch. Phase 0 also records the changes that were in the working tree before the run, so that Phase 5 does not commit them.
- `gop-work` (issue #58): a change to `Directory.Packages.props` or another shared build file, with no `.cs` or `.csproj` change, skipped all tests. Behavior change: such a change now runs all test projects. `gop-test` has a new input `test_scope` for this.
- `gop-work` (issue #58): a failed build, or a test that failed because of production code, stopped the run, also with `--autonomous`. `gop-test` must not change production code. Behavior change: the run now goes back to Phase 1 with the failures, and the main session fixes the production code. The run does this at most 2 times, and then it stops and reports the failures.
- The five `gop-validate-*` validators (issue #58): a rule made a failed build or test CRITICAL. The rule never applied, because the run stops or starts a fix cycle before the validation. The rule is gone. The validators still record "no tests found" as INFO.
- `gop-work` (issue #58): the skill now states that its build and test phases assume a .NET solution and the .NET SDK on `PATH`.
- `gop-test` (issue #58): the agent polled the log of a long test run with `sleep` loops. When the background command of a background subagent ends, Claude Code sends the subagent a notification. The agent now waits for that notification and then reads the exit file and the log. `gop-work` now starts `gop-test` as a background subagent, and the agent file sets `background: true`. So the notification arrives.

### Changed in gop-pipeline

- `plugin.json` (issue #58): the plugin declares `dev-essentials` as a dependency, because `gop-work` and `gop-test` use its skills and agents. An install of `gop-pipeline` now also installs `dev-essentials`.

### Changed in dotnet-backend-dev

- `plugin.json` (issue #58): the plugin declares `dev-essentials` as a dependency, because some of its skills use skills of `dev-essentials`. An install of `dotnet-backend-dev` now also installs `dev-essentials`.

### Changed in the repository

- `README.md` (issue #58): the rules for `plugin.json` allow the `dependencies` field, with bare plugin names and no version range. The install section says that `dotnet-backend-dev` and `gop-pipeline` also install `dev-essentials`.

## dev-essentials 3.3.1 and gop-pipeline 1.3.1 in release [3.3.1] - 2026-10-22

This release follows up on issue #55. Some skill text named a versioned model, or quoted the higher price that one model charges for a long prompt. Other text cited the docs as the reason for a rule. When a new model or a new docs page ships, such text goes out of date. The text now gives a reason that stays true, and names models only by family. No behavior changes.

### Fixed in dev-essentials

- `subagent-orchestration` (issue #55): the auto-compact rule no longer names Haiku 5.5, its price for a long prompt, or the docs. It now says that about 100,000 tokens is a good size for search, fact, and build-check work. The reason is that a larger context often costs more and adds noise. The skill no longer says which model the built-in `Explore` agent runs on. It now says not to count on `Explore` for a cheap search, because its model can change between releases.
- `review-loop` (issue #55): the examples name the reviewer model as `opus`, not as a versioned model ID.
- `bug-hunt` (issue #55): `references/pauses.md` no longer says that its facts come from the docs.
- `audit-personal-conventions` (issue #55): `references/entity-authoring-conventions.md` gives the reasons for the 500-line rule and the `context: fork` rule without a quote from the docs.

### Fixed in gop-pipeline

- `gop-work` (issue #55): the Phase 0 text and the Stages table no longer say which model the built-in `Explore` and Plan agents run on.

## dev-essentials 3.3.0 and gop-pipeline 1.3.0 in release [3.3.0] - 2026-10-22

The workflows now give the mechanical work to three new read-only Haiku agents: a code search, fact gathering, and a build and test check (issue #55). The planning, the review, and the implementation stay on their models. A built-in `Explore` search runs on the model of the session, so the workflows now use the new code search agent. The new agent fields need Claude Code 2.1.296 or later for `autoCompactWindow` and 2.1.271 or later for `omitClaudeMd`. An older version loads the agents without these fields. The per-call `effort` parameter of the Agent tool needs 2.1.292 or later. Three workflows now also name an effort level for each role: `research-implement-review-report`, `implement-batch`, and `review-loop`, so that a subagent does not depend on the effort of the session.

### Added in dev-essentials

- `code-locator` (issue #55): a read-only code search agent. It returns paths, line numbers, symbols, and short excerpts.
- `fact-gatherer` (issue #55): a read-only agent for one narrow question. It returns facts with a `path:line` or a URL as evidence, and no conclusions.
- `test-runner` (issue #55): an agent that runs the build and test commands of a brief and reports the verbatim result lines. It never edits code. In a .NET repo, it follows `dotnet-build-test`.

### Changed in dev-essentials

- `subagent-orchestration` (issue #55): "Haiku scope" names the three agents and the rule that they return facts, not synthesis. The skill says that the built-in `Explore` runs on the model of the session, and that only an agent file sets the auto-compact window. A plan now names exact paths, anchors, and key signatures. A new, rarely used exception gives a small, tightly coupled task to a fork on an Opus session. A new section says that the orchestrating session runs on Opus or Sonnet, never on Haiku. On a Sonnet session, a tightly coupled task and a critical decision without the user go to an Opus subagent. In Rule 5, each dispatch of a general agent type passes `effort`. Any other agent type gets `effort` in two cases: a skill or the user names a level, or the session effort is too low for the task. It says which dispatch needs no `effort` parameter. It also warns against `CLAUDE_CODE_EFFORT_LEVEL`, because that variable overrides the effort of every subagent. Behavior change: item 1 of `Trust but verify` checks a build or test claim with `test-runner`, with the same test filter as the subagent.
- `research-implement-review-report` (issue #55): Phase 1 dispatches parallel fact gatherers, one narrow question each, and then a planner that reads their reports. A question that needs judgment goes whole to a researcher. Behavior change: after each task, the orchestrating session checks the build and the tests with `test-runner`. The "Models" line names every role. Behavior change: a new "Effort" line sets the effort of each research, planning, and implementation dispatch.
- `implement-batch` (issue #55): the "Models" line agrees with RIRR. Behavior change: Step 3 checks the build and the tests with `test-runner` before the commit. Behavior change: a new "Effort" line, which agrees with RIRR, sets the effort of the planner and the implementer.
- `implement-task` (issue #55): behavior change: the simplify pass gets a `test-runner` check before its commit.
- `feature-pipeline` (issue #55): behavior change: the Build Gate gives the build to `test-runner`, and the master agent reads only its report.
- `review-loop` (issue #55): behavior change: Phase 6 runs the build and the tests through `test-runner`. A reviewer can give a broad search to `code-locator`. Behavior change: in the orchestrated mode, the Area Explorers and the Finding Verifier run on `--reviewer-model`. Behavior change: the Target Explorer of the orchestrated mode runs on Haiku with low effort. It returns a fact map with no judgment, and the Area Explorers do the judging. Behavior change: each dispatch on the reviewer model now passes the effort of the new option `--reviewer-effort` (default `high`). The fixer passes the effort of `--fixer-effort` (default `medium`).
- `help-review-pr` and `audit-team` (issue #55): a review can give a broad search to `code-locator`. `audit-team` does not use it for a role. Behavior change: the orchestrated mode of `help-review-pr` changes the same way as in `review-loop`, with a Target Explorer fact map.

### Changed in gop-pipeline

- `gop-work` (issue #55): if the session lists `dev-essentials:code-locator`, Phase 0 uses it for a code search. Else it uses the built-in `Explore`.

## dev-essentials 3.2.3, dotnet-backend-dev 1.4.3, and gop-pipeline 1.2.5 in release [3.2.3] - 2026-10-18

Some instructions in the skills, agents, and commands were wrong or misleading. Some told Claude to do a thing that cannot work, for example to ask the user from a subagent. Some contradicted another file, and some code examples did not compile or did the wrong thing. This release fixes them (issue #48). Each fix below says what was wrong and what the text says now. Where a fix changes behavior on purpose, the bullet says so. The release also ships the `.gitattributes` file of issue #52, which had no release before.

### Fixed in dev-essentials

- `audit-personal-conventions` (issue #48): the review-fix commits were called "Apply review findings" and had to hold the finding numbers, but the review loop makes its own `Review round <N>: Fix ...` commits. The skill now keeps the finding numbers and their `source:` citations in the report of Phase 10, not in commit messages. Behavior change: the extra "Apply review findings" commit is gone. A new rule picks the terms that a shipped entity must still cover, and it has its own section in `entity-authoring-conventions.md`. A resume run now stops and asks in two cases. In the first, the TODO has no `Marketplace remote`, on every path that resolves the marketplace root. The run asks for the remote URL and writes the answer into the TODO. In the second, a `--marketplace=` clone has no `origin` remote. Before, it went on with a warning, and the later compare never passed. An approved F item in a memory file is removed with the once-per-run question. An F item in a CLAUDE.md is only reported. A stale personal file is deleted only after the user approves its F item at Phase 5. The resume hints now say so. The skill also tells the worktree skill to leave `.gitignore` of the other repo alone. The report templates and the walkthrough now show the sections that the Phase 10 report has.
- `project-claude-md-preamble` (issue #48): if the root has both `CLAUDE.md` and `AGENTS.md`, Claude Code reads only `CLAUDE.md`. A preamble in `AGENTS.md` alone did not load. The skill now keeps the preamble in `AGENTS.md` and puts the line `@AGENTS.md` in `CLAUDE.md`.
- `bug-hunt` (issue #48): the planner now numbers the areas in search order. If the user changes the order, the planner renumbers the areas. Before, the number and the order did not always agree. A structure check that fails on the setup files, the digest, or the skeleton now names the agent to run again. Before, the text had only a repair step for hunters, verifiers, and the auditor.
- `create-documentation` (issue #48): the REST API template listed two links in its contents list ("Update" and "Delete") that have no section. The links are gone.
- `create-html-artifact` (issue #48): the Mermaid note said that single-encoded entities such as `&lt;` break a diagram. Mermaid decodes one level, so only double-encoded text fails. The note and its search list now look for the double-encoded form.
- `dotnet-build-test` (issue #48): the text said a foreground Bash command runs for 10 minutes by default. The default is 2 minutes, and the `timeout` parameter raises it to at most 10 minutes. The steps for a subagent now give each wait call a `timeout` of at most `600000`.
- `feature-pipeline` (issue #48): the skill now tells the stages where it lives, so the path of the starter context file works. The flags reach the skill through `$ARGUMENTS`. Every stage prompt now gets a `<worktree>` block, so stage commands run in the worktree and not in the main checkout. The text no longer mixes `<task-id>` and `{TASK_ID}`. Behavior changes: when a resumed run needs the Build Gate or Human Approve #2, it now runs them. A fix round now runs the implementation stage again and then the Build Gate. A stage that reports a STOP, a blocker, or an escalation is not marked complete. The skill asks the user in every mode. A missing `stageStartSha` entry no longer stops a resume. The worktree skill now gets the base branch of the project context. The finalization stage reports the PR number, owner, and repository. The test plan heading in the table now matches the real heading.
- `git-worktree-management` (issue #48): `git check-ignore` and `git rev-parse` now run with `git -C <repo-root>`, so they work from any folder. The exclude path is absolute. The `--track` option is gone from the command for a remote branch, because the command failed for a branch with no upstream. The copy of `settings.local.json` now reads from the repo root and creates the target folder. The solution search finds `.slnx` files too. The advice for long paths no longer says to shorten the branch ref. It says to suggest a shorter branch name to the user.
- `optimize-skill` (issue #48): when a fact test fails after a commit, the repair now changes the commit of this step, with `git commit --amend`. If that commit exists and its parent is the base commit of the step, the repair amends it. Before, the repair sometimes added a second commit for the same step. If the commit does not exist, the repair makes it. The repair never amends the base commit of the user. The `SendMessage` repair, the dispatch again, and the briefs carry the same instruction.
- `process-pr-comments` (issue #48): `deep-fix` took a thread ID, but the reply and commit text use the number of the top comment (`T#`). The option now takes the comment ID and says so. Subagents cannot push after they ask the user, so the push moved. Behavior change: the orchestrating session now pushes on every cycle, and then resumes Stage 2 for the resolve step and Phase 5. If no push happens (no go-ahead, the user declines, or the push fails), Stage 2 runs Phase 5 only. The orchestrating session also owns `processedCommentIds`. On `stop-blocked`, the deep-fix commits stay on the unpushed branch and are not squashed. The deep-fix review runs on the range of that arc only. In autonomous mode, an `[OutOfScope]` issue takes its title from the draft and no type unless the reviewer named one. An autonomous reply to a `[Question]` is a plain `[AI]` reply. The skill states that creating a PR is out of scope and points to `pr-composer` for the text only. Behavior change: with `autonomous`, a fix that rewrites code from scratch (Bucket A2) must now stay inside the diff of the PR. Before, it was allowed to leave the diff.
- `review-loop` (issue #48): the run format changes only what chat shows. The text said it also moved the reports to files, and it named a `--print-reports` override that does not exist. The text now says that the report destination does not change. The `audit-team` reviewer builds its own prompts, so Phase 3 builds no brief for it. The triage table showed "(will fix)" for every row, even for a finding that was deferred on its merits. Rows now show the merit deferral. The `blocker` skip token now says that the finding goes to the deferred list of Phase 9. Behavior change: a finding that a primary source refuted no longer blocks `stop-clean`. The examples now match the rules, and they no longer cite a convention that does not exist. The spec review example now works for the change document of any spec framework, with OpenSpec as one case. It uses the active-change path `openspec/changes/<name>/` and the archive path `openspec/changes/archive/<YYYY-MM-DD>-<name>/`, as the OpenSpec docs give them.
- `subagent-orchestration` (issue #48): the rule against background Bash runs named one exception. It now names both exceptions of `dotnet-build-test`: an explicit request of the user, and a long test run in a subagent.
- `trim-artifacts` (issue #48): the planner copied only its own batch, so the planner had no proof for a regular expression that crosses files. It now copies every file that the glob matches. Each batch has its own scratch folder and its own progress file, so parallel planners no longer overwrite each other. The reviewer brief now has a `Targets in bytes: {TARGETS}` line. Each plan names the profile of each file. So the reviewer can check each file against its target.
- `write-markdown` (issue #48): the skill told Claude to install `markdownlint` and to create a configuration file on its own. Behavior change: it now does neither unless the user asks. It uses the existing configuration of the repo, and the setup notes are for the user.
- `docs-composer`, `pr-composer`, and `task-composer` (issue #48): the agents said to ask the user, but a subagent has no way to ask. They now stop and put the question in the final reply, so that the caller asks. The `pr-composer` file name is now `PR-<branch>.md`. Each `/` in the branch name becomes `-`, because a slash in the name made a folder.
- `implement-batch` (issue #48): the text allowed a Step 2 with no plans commit, which broke the squash base of task 1. Behavior change: Step 2 now always makes one plans commit, and stages the plan files again before the squash. The review of task 1 now starts at that commit (`REVIEW_BASE_SHA`), so it no longer reviews the plan files as code.
- `implement-task` (issue #48): a research agent that cannot fetch an item, and a simplify step that needs a decision, said to ask the user. Subagents cannot ask. They now stop that item, and put the question in their report for the orchestrator.
- `implement` and `opsx-implement` (issue #48): the examples named `create-domain-model` and `create-tests` and assumed that every repo has them. They now name the `dotnet-backend-dev` skills. They say that these skills apply to a .NET repo with that plugin.
- `merge-worktree-projects` (issue #48): the index merge dropped the pointer line of a memory file that had no free name and did not move. Now such a line is not appended. The index of the worktree project stays in place for that pair only, and the report lists the pair as partially retained. Every other merge still deletes the copy of the index. The text points to the right step (4.5) for the deletion.
- `research-implement-review-report` (issue #48): a plan file as the argument now skips research and planning, but still gets the sign-off and the open-decision step. In single mode, Phase 2 output is committed before Phase 3. Behavior change: if the review loop ends with `stop-blocked`, the command no longer squashes. It keeps the round commits and reports the verdict.

### Fixed in dotnet-backend-dev

- `add-configuration-option` (issue #48): the `appsettings.json` section was `{Feature}`, but the options binding uses the name of the options class. The section is now `{Feature}Options`, and the text says why. The environment variable example now shows how the key maps to the shell variable. A comment in the example validator says that the nested validation is for nested options only. Behavior change: the default way to read options is now `IOptionsMonitor<T>`, as in the conventions. `IOptions<T>` and `IOptionsSnapshot<T>` stay for repos that already use them.
- `add-migration` (issue #48): the container example used a per-entity `ToContainer` and a partition key, which contradicts the entity configuration of the conventions. Behavior change: a new entity now uses the service container from `DbStorages`, as in `create-ef-entity`. The separate-container example is only for a change of the partition key. The batch pattern in `common-patterns.md` used `Skip`. When the batch removes or changes the rows that the query filters on, `Skip` misses records. The pattern now queries the records that still need the migration and takes a batch each time. It keeps the keys of skipped records out of the query. It works for any key type, for example `Guid`.
- `add-session-logging` (issue #48): the example wrote the failure as an information entry and kept the exception out of the log. It now writes an error entry with a user-friendly message, passes `ex.ToString()` in `details`, and uses `CancellationToken.None`. Behavior change: the exception text now goes to the `details` parameter, as `logging.md` says.
- `create-controller` (issue #48): the text said to implement `I{Feature}ControllerImpl`. The class is `{Feature}ControllerImpl`, and it implements the generated `Rest.I{Feature}Controller`.
- `create-domain-model` (issue #48): the skill told Claude to write `Equals`, `GetHashCode`, and `ToString` by hand with a case-insensitive comparer. This contradicted the hub, which keeps the generated members. Behavior change: the skill now keeps the generated members unless a case in `domain-models.md` applies. The fallback for a missing `IStaticEquatable<T>` is `IEquatable<T>, IEqualityOperators<T, T, Boolean>`, and the line that said to drop the interface is gone. `dotnet-conventions` and `domain-models.md` say the same.
- `create-ef-entity` (issue #48): the repository interface path was wrong. The example used a raw container name and a partition key. It now uses `DbStorages`, `HasUniversalKey`, and no partition key, as in `ef-patterns.md`. The skill had no step for the repository class or the `DbSet` property. It now has both.
- `create-exception` and `create-string-resource` (issue #48): the example messages put some placeholders in no brackets. The messages now wrap each value in `[{0}]`, as the string rules say.
- `create-tests` (issue #48): the rule for optional parameters did not cover the `Create{Mock}` helpers. It now does. The two constructor tests are now required for one or more dependencies, not more than one. The examples now match the rules. Comments no longer put text after "Arrange" on the same line. The logger helper is non-static and passes the fixture. The mock builder uses `Arg.Any<T>()` with `Returns`. The repository tests use `CreateRepository(DbContext)` and no extra `SaveChangesAsync`. The scenario tests use `CreateNew()` and `FromValue()`. The wrapper tests use a `CreateMigrationId` helper of the generator. The controller test uses a generator method and a 503 service-unavailable assertion. The migration test uses a helper for the legacy record. Every test class example now has `[TestFixture]`, also a generic one with `[TestFixtureSource]`. The rules say so too. No example file that has no regions has a banner comment above its helpers. The helpers stay at the end of the class. `enforced-gates.md` says that the other examples leave out the regions.
- `model-mapping` (issue #48): `nameof(A.B.C)` returns only `C`, so the nested `MapProperty` examples mapped the wrong property. They now give the path as an array of names. The `using` alias in an example is now `Rest = ...`.
- `update-swagger-spec` (issue #48): the standard error responses had a 500 with no body. Every operation must document 500, because otherwise an unhandled server exception can look like a client failure in some generated client code. The 500 now has a `ProblemDetails` body, and the spec also documents a 503 with a `ProblemDetails` body. The checklist, the worked example, and the first full operation example ("Path Operations") list 500. The integration test example now adds a store to the database first, because the database is empty after each test.

### Fixed in gop-pipeline

- `gop-build` (issue #48): the build walked up only from modified `.cs` files. It now walks up from any modified file, and a modified `.csproj` counts as affected. If no project is affected and no shared infrastructure changed, it builds the solution.
- `gop-commit` (issue #48): `cd <repo_root>` does not persist between Bash calls, so the git commands ran in the wrong folder. Every git command now uses `git -C <repo_root>`. The pathspecs that unstage `CLAUDE.md` and plan files now work from the top of the repo.
- `gop-test` (issue #48): the test build used `--no-restore`, which failed on a project that was not restored. The flag is gone. A modified `.csproj` file now counts as a source project.
- `gop-validate-compliance`, `gop-validate-correctness`, `gop-validate-performance`, `gop-validate-reuse`, and `gop-validate-security` (issue #48): `git diff HEAD` does not show new untracked files. The validators now also list the untracked files with `git ls-files --others --exclude-standard`, and read each one in full. Behavior change: validators now review new files, which they missed before.
- `gop-work` (issue #48): the quick probe for a test project is gone. Behavior change: if any `.cs` or `.csproj` file changed, Phase 3 now runs, and `gop-test` does the search. In interactive mode, after the second re-run, the options "accept" and "dismiss" are gone. A `BLOCKED` result stops the pipeline. A result with warnings offers only to proceed or to stop for a manual fix. The implement stage now also runs `git status --short`, so new files show in the scope.

### Changed in the repository

- `.gitattributes`: new file. GitHub counts the `.md` files in the language statistics, so the main language of the repository is Markdown, not Python (issue #52).

## dev-essentials 3.2.2 and dotnet-backend-dev 1.4.2 in release [3.2.2] - 2026-10-18

This release reviews each lint exception of the repository (issue #49). Text rewrites and a fix in the lint test remove 14 of the 23 entries of the simple-english baseline. The 9 entries that stay name the reason that no rewrite can remove them. Two markdownlint rule changes go away.

### Changed in the repository

- `tests/simple-english-baseline.json`: 9 entries instead of 23. The reason of each entry that stays names the settled name, the file path, or the quoted source that keeps the hit.
- `tests/test_simple_english.py`: the test does not lint the value of an `argument-hint` line or the closing `---` of the frontmatter, because they are not prose. Before, the hint and the first sentence of the body counted as one long sentence.
- `.markdownlint.jsonc`: `MD038` is on again. `MD033` allows only the elements of the `write-markdown` base configuration. `MD041` names its reason.

### Fixed in dev-essentials

- `merge-worktree-projects`: the text uses "approval" for the answer of the user and keeps "check" for the safety checks. The report line for a skipped folder is now "skipped (recent activity). Make sure that it is safe to merge."
- `bug-hunt`: placeholders such as `<ID>` in the notes are code spans. The "Result:" text of a verifier is a code span with no space at the start. The text says to add a space before it.
- `audit-personal-conventions`: the gate question before the delete is two short questions.
- `feature-pipeline`: the worktree announcement has no bold labels, and the project context template uses placeholders that markdownlint does not read as HTML.
- `general-conventions`, `review-loop`, and `task-composer`: plain words in a YAML rule, in an example of a bad argument, and in a trigger phrase.

### Fixed in dotnet-backend-dev

- `create-tests`: the checklist item for Gate 1 states the gate first and its scope in two short sentences. The scope does not change.

## dev-essentials 3.2.1 and gop-pipeline 1.2.4 in release [3.2.1] - 2026-10-18

Many skills and commands have options that set a model, for example `--reviewer-model` and `--fixer-model`. Their text also named the default model of a role ("the Opus reviewer", "a Sonnet fixer"). If the user picked another model with the option, that text contradicted the run. The text now names the option or the role. The default model appears once, in the option table or the model line of the skill (issue #47).

### Changed in dev-essentials

- `review-loop` (issue #47): the phases, the audit-team adapter, and the examples name `--reviewer-model` and `--fixer-model` instead of Opus and Sonnet. The option table keeps the defaults.
- `bug-hunt` (issue #47): if the model of the hunter, the verifier, or the auditor is not available, step 0 asks a question. Before, only a missing Fable gave this question. The helper briefs no longer repeat the models of the dispatch table.
- `process-pr-comments` (issue #47): the intro, the note under the dispatch table, `references/thread-state-schema.md`, and `references/deep-fix.md` no longer name the models of the stages. The dispatch table is their one home.
- `implement-batch` and `research-implement-review-report` (issue #47): the steps name the role, for example "planner" or "implementer". The "Models" line is the one home of the models.
- `audit-personal-conventions` (issue #47): the example of session review-loop defaults and the walkthrough no longer name models.
- `audit-personal-conventions`, `git-worktree-management`, `implement`, `opsx-implement`, `process-pr-comments`, and `save-context` (issue #47): the "Autonomy" section no longer has the rule for a Fable dispatch. These workflows never pick Fable on their own. The rule stays in the workflows that can pick Fable, and its one home is "Model selection" in `subagent-orchestration`.

### Changed in gop-pipeline

- `gop-work` (issue #47): the "Autonomy" section no longer has the rule for a Fable dispatch. The workflow uses the fixed models of its agent table and never picks Fable.

## dev-essentials 3.2.0 in release [3.2.0] - 2026-10-18

This release adds the skill `optimize-skill` (issue #26). It turns the pipeline that optimized `bug-hunt` and the other skills of this marketplace into a skill.

### Added in dev-essentials

- `optimize-skill`: a skill that optimizes one skill for tokens and clarity and keeps its behavior. An auditor (Opus by default) reads the skill docs, the best practices for skills, and the criteria of `claude-md-improver`. It writes an audit report with a fix plan for each item. The orchestrator decides the open items from the decisions of the user, not from the taste of the auditor. By default, it decides them without a stop and lists them for review. With `--interactive`, it asks. An applier (Sonnet by default) classifies each item APPLY, PARTIAL, or REJECT, applies the plan, and makes one local commit. A reviewer (Opus by default) then tests whether the skill still behaves the same. A fixer (Sonnet by default) applies the accepted findings in a second commit. The run never pushes. If `simple-english` is not installed, the run uses the plain-English fallback rules of `bug-hunt`.
- `optimize-skill`: the reference files `audit-report-format.md` and `briefs.md`, and the worked example `examples/bug-hunt-audit.md`, an abridged copy of a real audit of `bug-hunt`.
- `plugin.json`: the keyword `skill-optimization`.

### Changed in the repository

- `tests/simple-english-baseline.json`: one entry for the worked example, which quotes the settled terms of `bug-hunt`.

## dev-essentials 3.1.1, dotnet-backend-dev 1.4.1, and gop-pipeline 1.2.3 in release [3.1.1] - 2026-10-18

When claude.ai synced the marketplace, it showed 5 warnings. This release removes them (issue #44). The release also adds the update steps to the README and cuts the text that repeated the documentation (issue #42).

### Added in the repository

- `tests/test_claude_ai_sync.py` (issue #44): a test for two problems. If a `plugin.json` sets `$schema`, the test fails. If the `description` of a skill, an agent, or a command holds an angle bracket, the test also fails.

### Changed in the repository

- `README.md` (issue #42): a new section "Updating the plugins" says how to get a new release. You run `/plugin marketplace update vasar-plugins-marketplace` and then `/reload-plugins`. The section also says how automatic updates work and how to turn them on for this marketplace.
- `README.md` (issue #42): the "Authoring reference" no longer repeats the official documentation. The sections about the folder structure, `marketplace.json`, `plugin.json`, and validation keep only the rules of this repository. They link to the documentation for the rest. The links in the intro and in "References" go to the current pages of the Claude Code documentation.
- `README.md` (issue #44): the rules for `plugin.json` no longer list `$schema`. They say not to set it, because the claude.ai sync strips it and shows a warning.

### Fixed in dev-essentials

- `plugin.json` (issue #44): removes `$schema`. Claude Code ignores the key, but the claude.ai sync strips it and shows a warning.
- `git-worktree-management` (issue #44): the description no longer holds the path `<repo-root>/.claude/worktrees/<full-branch-ref>/`. claude.ai read the placeholders as XML tags and removed the angle brackets, so the path was broken on claude.ai. The description now names the `.claude/worktrees/` folder of the repo in words. The body keeps the full path.
- `audit-personal-conventions` (issue #44): the description recipe in `references/entity-authoring-conventions.md` has a new item. A `description` must not hold angle brackets.

### Fixed in dotnet-backend-dev

- `plugin.json` (issue #44): removes `$schema`. Claude Code ignores the key, but the claude.ai sync strips it and shows a warning.

### Fixed in gop-pipeline

- `plugin.json` (issue #44): removes `$schema`. Claude Code ignores the key, but the claude.ai sync strips it and shows a warning.

## dev-essentials 3.1.0 and dotnet-backend-dev 1.4.0 in release [3.1.0] - 2026-10-17

This release closes the gaps between the descriptions and the bodies that remained after release 3.0.2 (issue #36). It makes `pr-composer` read the spec or the plan of a branch (issue #40). It makes `/write-tests` dispatch the `test-engineer` agent (issue #37). It adds a serialization rule to `handle-sensitive-data` (issue #39). It replaces the names of replaceable tools in the bodies with general terms (issue #38).

### Added in dev-essentials

- `pr-composer`: a step that finds the spec or planning artifact of the branch (issue #40). The agent looks at four sources. The first is the brief. The second is the active changes of the spec framework. The third is plan and design files in the plan folders and notes folders. The fourth is decision records that the diff adds or changes. An artifact belongs to the branch in three cases. The brief names it, the diff adds or changes it, or its name holds the slug or an issue number of the branch. The slug or the number must be a whole part of the name. The agent uses the artifacts for the reason of the change. It names each artifact that it used, with its path, in its final reply. It does not fetch an issue from a remote system.

### Changed in dev-essentials

- `pr-composer` (issue #40): the agent now always reads the git diff first. Before, an active OpenSpec change was the only source for the PR description, and the agent skipped the diff. Now the agent reads the diff together with the artifacts. The diff gives what changed. The artifacts give the reason. If an artifact plans work that the diff does not hold, the agent says so in the "Notes" section. A change of the spec framework must belong to the branch. If exactly one active change exists, it counts as the change of the branch. If no rule matches it, the agent names it as a guess in its final reply. If another artifact belongs to the branch by a rule, the PR description does not use the guess. Otherwise, the "Notes" section does not list the planned work of that change. The description of the agent and the description of `/compose-pr` follow the new behavior.
- `compose-pr` (issue #40): the brief for the agent now holds each spec, plan, or design document that the user named, as a path. It also holds the text of each linked issue or task that the user gave, word for word. The command does not fetch an issue. It shows the artifacts, the guesses, and the issue numbers without text that the agent names in its final reply.
- The bodies use general terms in place of tools that a project can replace (issue #38). A body names such a tool only as a marked example, for example "the mapping library (for example, Riok.Mapperly)". This applies to `general-conventions/powershell.md`, where AWS and Azure are now examples of a cloud provider. It also applies to the other skills and references that named a replaceable tool.
- `audit-personal-conventions` (issue #38): `references/entity-authoring-conventions.md` extends the rule for general terms to the body and to the `keywords` of `plugin.json`. Only a plugin that exists for a tool can use its name as a keyword. The file asks for one general term for each role in all files of the marketplace. It asks for an example at the first use of the term in a file. A new section lists the allowed forms of a marked example and has a table of the general terms.
- `keywords` of `plugin.json` (issue #38): `openspec` becomes `spec-driven`.
- `implement-task`, `implement-batch`, and `research-implement-review-report` (issue #38): the line about `feature-pipeline` was wrong. It said that the pipeline is for an OpenSpec change. Now it says that the pipeline runs a tracked task from the task provider end-to-end in an isolated git worktree.

### Added in dotnet-backend-dev

- `handle-sensitive-data`: a section about serialized output (issue #39). A serializer does not call `ToString()`, so the placeholder did not protect the JSON form of a secret. The section has three parts. The first is an example of a `System.Text.Json` converter that writes the placeholder. The second is a rule for secrets in plain `String` properties. The third is a table that says what to do for logs, API responses, caches, and messages. The section also says how an inbound model reads a secret. It also lists three cases in which the `[LogProperties]` attribute logs a raw value. The checklist and the questions of the skill cover the new rule.

### Changed in dotnet-backend-dev

- `/write-tests` (issue #37): the command no longer writes tests in the main session. It parses the targets, merges the targets that overlap, and dispatches one `test-engineer` agent for each target. A target is a class, a module (a folder or a namespace), or an assembly (a project). Independent targets run in parallel, at most four at the same time. The command checks the combined result and shows one merged report.
- `test-engineer` (issue #37): the agent handles class, module, and assembly targets. It reads a brief from the command and returns a short report in a fixed format. A module or an assembly with more than 20 classes gets no tests. The agent reports the classes, and the command splits them into class targets of at most 20 classes.
- `handle-sensitive-data` (issue #39): the description and `when_to_use` name the serialized form. `dotnet-conventions/security.md` gets a line that points to the skill for JSON.
- The bodies use general terms in place of tools that a project can replace (issue #38). Examples are the code generator, the OpenAPI linter, the mapping library, and the validation library. Other examples are the document database, the test framework, the assertion library, the mocking library, and the test data library. The concrete tools stay as marked examples. This applies to the skills, the examples of `create-tests`, `dotnet-conventions`, and the `test-engineer` agent.
- `keywords` of `plugin.json` (issue #38): `nswag` becomes `code-generation`, and `mapperly` becomes `object-mapping`.

## dev-essentials 3.0.2, dotnet-backend-dev 1.3.2, and gop-pipeline 1.2.2 in release [3.0.2] - 2026-10-17

This release shortens the descriptions that Claude Code loads into every session (issue #33). The skill listing has a budget of 1% of the context window. If the listing is over the budget, Claude Code drops the descriptions of the skills that you use least. Without its description, Claude cannot match a skill to a request. Each new description puts the main use case first and keeps the strongest trigger phrases. The details stay in the body of each file. The release also adds status badges to the README (issue #32).

### Added in the repository

- `README.md`: a line of badges under the title. The tests badge shows the result of the `Tests` workflow on `main` and links to the workflow runs. The latest release badge links to the latest GitHub release. The MIT license badge links to `LICENSE`. The Claude Code plugin marketplace badge links to the documentation of plugin marketplaces. The latest release badge reads the GitHub API through shields.io, so it can show an error while the repository is private.

### Changed in the repository

- `.claude-plugin/marketplace.json` and `README.md`: the descriptions of the marketplace and of each plugin state the general purpose in one to three sentences. They no longer list skills.
- `tests/simple-english-baseline.json`: removes the two entries that the old descriptions needed.

### Changed in dev-essentials

- Shorter descriptions for the skills, commands, and agents. `audit-personal-conventions` also has a shorter `when_to_use`. The three bug-hunt agents still say that only the `bug-hunt` skill dispatches them.
- The trigger phrases of each skill move from `description` to a new `when_to_use` field, so `description` says what the skill does. The agents keep their trigger phrases in `description`, because the frontmatter of an agent has no `when_to_use` field. `feature-pipeline` gets no `when_to_use`, because Claude Code does not load its description.
- If an entity does not exist for a library, a product, or a file, its description does not name it. The descriptions also leave out the internal mechanics. For example, `pr-composer` no longer names OpenSpec, and `process-pr-comments` no longer names its review tags.
- `implement-task` and `implement-batch`: the description says that the command pushes only with `--push`. The old text said that it never pushes.
- The plugin description states the general purpose and lists no skills.
- `audit-personal-conventions`: the description recipe in `references/entity-authoring-conventions.md` follows the new short style. A new description puts the main use case first and has a few trigger phrases. It keeps the facts that change what the user expects, for example a stop before a push. The other details go in the body. The recipe also asks for general terms in place of the names of tools and types that a project can replace. It asks to leave out internal mechanics. It also says which entities get `when_to_use`. Skills and commands get it, and agents do not.

### Changed in dotnet-backend-dev

- Shorter descriptions for the 15 skills and the `test-engineer` agent. The trigger phrases of each skill move to a new `when_to_use` field.
- The descriptions use general terms in place of the names that a project can replace. Examples are the code generator, the mapping library, the test libraries, and the validation library. Other examples are the database product, the session log type, and the resource file name. EF Core and OpenAPI stay.
- The plugin description states the general purpose and lists no skills.

### Changed in gop-pipeline

- Shorter descriptions for the `gop-work` skill and its 8 agents. Each agent still says that only `gop-work` dispatches it. `gop-work` moves its trigger condition to a new `when_to_use` field.
- The plugin description states the general purpose and lists no skills.

## dev-essentials 3.0.1, dotnet-backend-dev 1.3.1, and gop-pipeline 1.2.1 in release [3.0.1] - 2026-10-15

This release adds tests for the scripts of the skills and lint checks for the `.md` files of the repository (issues #25 and #28). The plugin changes fix the Markdown and the words that the new checks found.

### Added in the repository

- The folder `tests/` with tests for `check_report.py` (`bug-hunt`) and `trim_report.py` (`trim-artifacts`). It also has a simple-english lint test and a markdownlint test for every tracked `.md` file of the repository. Run `python3 -m unittest discover -s tests -v` from the repository root. Claude Code does not copy this folder into the plugin cache.
- The file `.markdownlint.jsonc` with the markdownlint rules for the `.md` files of the repository.
- A GitHub Actions workflow that runs the tests on each pull request and on each push to `main`. It uses the latest release of the simple-english linter.

### Changed in the repository

- `CLAUDE.md`: shorter sentences and plainer words, so that the file passes the simple-english test. The rules did not change.

### Fixed in dev-essentials

- The Markdown of 10 files now passes markdownlint. The changes add blank lines around lists and code blocks, give each code block a language, and replace emphasis that worked as a heading. `create-documentation` no longer turns the line-length rule back on.
- `create-documentation`: the configuration, migration, and REST API templates no longer hold inline markdownlint comments, so the documents that an agent writes from them have none either. Two links of the configuration template were split over two lines and did not render as links. Each link is now on one line and renders. The skill also has a hint for a table row that passes the line-length limit of the target repo.
- `implement-batch`, `implement-task`, and `research-implement-review-report`: removed an inline markdownlint comment that the repository configuration already covers.
- `process-pr-comments`, `subagent-orchestration`, and `write-markdown`: shorter sentences and plainer words in four lines. The meaning did not change.

### Fixed in dotnet-backend-dev

- `add-migration`: two steps for a failed migration use plainer words. `create-primitive-wrapper` and the wrapper example of `create-tests` no longer use "etc.".

### Fixed in gop-pipeline

- The Markdown of 11 files now passes markdownlint. In `gop-work`, the two sub-steps of step 12 are now nested under the step.

## dev-essentials 3.0.0 and dotnet-backend-dev 1.3.0 in release [3.0.0] - 2026-10-14

This release makes the continuation prompt of `save-context` opt-in (issue #23). It also moves the .NET test tools from `dev-essentials` to `dotnet-backend-dev` (issue #24).

### Added in dotnet-backend-dev

- The command `/dotnet-backend-dev:write-tests` and the agent `dotnet-backend-dev:test-engineer`. Both moved from `dev-essentials` and work as before. They use the skill `create-tests` of the same plugin.

### Changed in dotnet-backend-dev

- `test-engineer`: If the agent cannot load `create-tests`, it now stops and reports the error. Before, it told the user to install `dotnet-backend-dev`.
- `test-engineer`: The agent now reads the `create-tests` examples from `${CLAUDE_PLUGIN_ROOT}/skills/create-tests/examples/` first. The search of the plugin cache stays as a fallback.
- The plugin description now names the `write-tests` command and the `test-engineer` agent.

### Changed in dev-essentials

- `save-context`: The next-session continuation prompt is now opt-in. The new flag `--continuation-prompt` prints it. A request in words also prints it. A run without a request cleans up the context files (Step 5) and prints no prompt. The flag `--no-cleanup` still skips the cleanup.
- `research-implement-review-report` and `implement-task`: The report phase now runs `save-context` as the last step of the run. The call passes no flag, also not `--plan` or the mode flag of the run. So `save-context` runs in its default mode, also in a run with `--autonomous`. Its cleanup keeps every file of the run, except a finished `_`-prefixed progress file, because the branch is not merged yet. Before it deletes a file of an older session, it asks the user. On a yes, the run deletes the listed files in the same session. `save-context` prints no continuation prompt, unless the user asks for one in the run.
- `implement` and `opsx-implement`: The commands no longer print the continuation prompt of `save-context` by default. If the user asks for it in the run, they print it after their summary.
- The plugin description no longer names a test agent.

### Removed in dev-essentials

- `save-context`: Removed the flag `--no-continuation-prompt`. The prompt is now off by default.
- Removed the command `write-tests` and the agent `test-engineer`. They moved to `dotnet-backend-dev`.

### Breaking changes in dev-essentials

- `/dev-essentials:write-tests` no longer exists. Install `dotnet-backend-dev` and run `/dotnet-backend-dev:write-tests`.
- The agent type `dev-essentials:test-engineer` no longer exists. Dispatch `dotnet-backend-dev:test-engineer`.
- `save-context` no longer accepts `--no-continuation-prompt`, and it prints no continuation prompt by default. To get the prompt, pass `--continuation-prompt`.

## dev-essentials 2.5.0 and dotnet-backend-dev 1.2.3 in release [2.5.0] - 2026-10-14

This release applies the design decisions from the lint sweep (issue #11).

### Changed in dev-essentials

- `process-pr-comments`: With `autonomous`, an automated-review fix that adds a new architecture or a new public contract is now implemented. Before, the skill drafted the fix and waited. Some such fixes also leave the files of the PR diff. If such a fix is not at the rewrite-from-scratch exception, the skill still drafts it and waits. The cycle log now has a list "Decisions for your review". The list names each decision that `autonomous` made in the cycle without a stop.
- `compose-pr`: The command now dispatches the `pr-composer` agent, so both write one PR description format, the format of `pr-composer`. `pr-composer` now ignores OpenSpec drafts and notes folders in the diff, and follows the extra context of the brief, as `compose-pr` did.
- `github-mcp-conventions`: Rule 4 now allows `delete_pending` for your own pending review. The ban on an edit or a delete of a posted comment through MCP stays.
- `subagent-orchestration`: Rule 3 now says that subagents run in the background by default, and how to dispatch independent work in parallel. It adds a short note on forks. The old text about the parameters of the `Agent` tool is gone.
- `review-loop`: The reference to Rule 3 of `subagent-orchestration` no longer speaks of a foreground or background choice. The branch-review example now prints `(parallel)`, not `(foreground-parallel)`.
- `create-documentation`: The feature template and the migration template now have a table of contents, as the checklist asks.
- `test-engineer`: The agent now names the combined comment forms `// Act & Assert.` and `// Arrange, Act & Assert.`.

### Changed in dotnet-backend-dev

- `create-tests`: Gate 1 now applies only to test classes that call the methods of the SUT directly. Controller tests through the HTTP client and scenario tests are out of its scope.
- `create-tests` and `dotnet-conventions`: The rule for test comments now names the combined forms `// Act & Assert.`, `// Arrange, Act & Assert.`, and `// Arrange & Act.`. The examples no longer use `// Act + Assert.`, and no longer put `// Act & Assert.` after `// Act.`.
- `create-tests`: The examples now end every section comment with a dot, as the rule says. For example, `// Arrange - empty database (cleared in SetUp).`.
- `handle-sensitive-data`: If it is not clear whether data is sensitive, the skill now asks the user. Before, it always asked. This matches `dotnet-conventions/security.md`.
- `dotnet-conventions`: `ef-patterns.md` and `domain-models.md` now give generic rules for stored references and for wrappers from a shared SDK. `security.md` no longer names a token type of one infrastructure domain.

## dev-essentials 2.4.2, dotnet-backend-dev 1.2.2, and gop-pipeline 1.2.0 in release [2.4.2] - 2026-10-14

This release fixes the skill bugs that the lint sweep found (issue #12).

### Added in gop-pipeline

- `gop-commit`: New optional input `warning_note`. A CRITICAL finding that the user overrides now reaches the commit message.
- `gop-commit`: New optional input `commit_trailer`. The agent now has a clear rule for the commit author and the trailer.

### Changed in dev-essentials

- `review-loop`: The option `--fixer` takes one agent ID. If the value names several agents (`audit-team`, `dual`, `pair`, or `quad`), the run warns and uses `general-purpose`.
- `process-pr-comments`: The default `bots` list now uses the real Copilot reviewer login `copilot-pull-request-reviewer[bot]`. The skill compares bot logins without the `[bot]` suffix.
- `feature-pipeline`: `--dry-run` now creates no worktree, no branch, and no file.
- `test-engineer`: The agent can now use the `Skill` tool to load `create-tests`. It reads the example files of the skill from the base folder that the Skill tool prints. Without that folder, it finds them in the plugin cache with Glob.
- `audit-personal-conventions`: The trigger phrases moved from `description` to the frontmatter field `when_to_use`. Claude Code adds this field to the description in the skill listing.

### Fixed in dev-essentials

- The lookup of a merged pull request now uses the head `owner:branch` and the state `all`. This applies to all workflows with the shared "Autonomy" section, `save-context`, and `git-worktree-management` (Workflow D). Before, the lookup missed some merged pull requests.
- `review-loop`, `help-review-pr`, and `github-mcp-conventions`: For a pull request from a fork, the diff recipe now fetches `pull/<id>/head`. `process-pr-comments` now runs the ancestry check against `origin/pull/<prId>/head`, so a pull request from a fork works.
- `git-sync`: The test for a rewritten branch uses `git merge-base --is-ancestor`. The repair recipe keeps the original author and date.
- `implement-batch`, `implement-task`, and `research-implement-review-report`: The guardrails now forbid the word "pre-existing" for a red signal, as `engineering-discipline` Rule 1 says.
- `review-loop`, `help-review-pr`, and `process-pr-comments`: The thread states now use the field names of the GitHub MCP response, `is_resolved` and `is_outdated`.
- `review-loop`: After a failed build or test run, Phase 7 commits the fixes first. Then Phase 6 runs the failing command on the commit before the fixes. If the main worktree holds uncommitted changes, Phase 6 also runs the command on the fix commit in a clean worktree. If the command fails only with the fixes, the loop tries one more fix. Else the loop stops with `stop-blocked` and the evidence. If the cycle has no fix, the loop stops with `stop-blocked` without this check. `engineering-discipline` Rule 1 names this check as an exception. The place of the cycle report now depends on `--rounds`.
- `audit-team`: The roles now run as `general-purpose` agents with a read-only brief.
- `feature-pipeline`: Stages 1 and 2 return `QUESTIONS`. The master agent asks the user. With `--autonomous`, it picks the recommended answers for at most 2 rounds, and lists them under "Decisions for your review". The master agent writes `review-diff.patch` against `origin/<base-branch>`, and saves the reply of the reviewer as `review.md`. A failed output check asks the reviewer for a new reply, not a new file. The security review also diffs against `origin/<base-branch>`. If its fetch fails, it writes the error to `security-review.md`, and the master agent stops and reports the error without a rerun. The text of the arguments follows the Autonomy core for the Fable rule, and every stage prompt gets the pipeline-discipline block. The RED step now proves that a passing test can fail, with a temporary wrong value. The run deletes `review-feedback.md` after each re-entry run. With `--skip=review`, `review.md` is optional.
- `process-pr-comments`: Bucket B now covers pushed history and commits that the run did not make, with an exception for deep fixes. Ordered rules replace "strictest action" for combined tags.
- `subagent-orchestration`: The Post-edit gate now covers only the edited paths, compared with the Pre-flight state.
- `audit-personal-conventions`: The skill creates the pull request with the GitHub MCP tools. If they are missing, or an MCP call fails with a connection or authentication error, it uses `gh pr create`. `github-mcp-conventions` names this step as the one exception to Rule 5. The skill fixes a call that fails because of a wrong parameter, and does not fall back. If `gh` is also missing or fails, the skill reports the PR text for a manual PR. The skill splits a skill that it authors and that grows past 500 lines. The authoring reference lists the split options: step references, scripts, agent files, `context: fork`, and an orchestrator skill.
- `task-composer`: The agent passes the approved issue type after a `list_issue_types` check. The agent always sets each existing label that fits the issue, with a type or without one. If the repository does not have the type, these labels include the label with the name of the type, if that label exists. The agent never creates a label.
- `pr-composer`: The agent has a fallback chain for the base branch. If the chain finds none, it asks in the final reply.
- `trim-artifacts`: The reviewer brief now has `{PLAN_PATH}` and the "in other file" test.
- The descriptions of `subagent-orchestration`, `process-pr-comments`, `audit-personal-conventions`, and `engineering-discipline` are now below the limit of 1,024 characters.
- `dotnet-build-test`: Rule 3 now has one exception for a subagent whose test run can take longer than 10 minutes. The subagent runs the tests in the background with a `timeout`, and polls an exit file. `subagent-orchestration` points to this exception.

### Fixed in dotnet-backend-dev

- `create-controller`: The example now inherits the project controller base.
- `add-session-logging`: The failure message of the session log no longer holds `ex.Message`. The session log field is now `_sessionLogRepository` in `add-session-logging`, `create-string-resource`, and `handle-sensitive-data`.
- `create-external-client`: The client no longer logs the whole request object.
- `model-mapping`: `SKILL.md` is now under 500 lines. `SKILL.md` no longer has the duplicate example.
- `dotnet-conventions`: The manual mapping example in `mappers.md` has its TODO and its parameter. The AAA example in `testing.md` builds the SUT with a helper named for its role.
- `create-tests`: The example in "Test Structure" builds the SUT with a helper named for its role. The usage examples in `generators.md` and `mock-builders.md` now follow the test rules. The test cases of the examples call private `Generate` helpers, not the generators. Rule 3 names `ExternalServicesMock` of Web API tests as the one exception to the no-post-setup rule. `repository-tests.md` uses one generic test class shape.

### Fixed in gop-pipeline

- `gop-test`: The agent runs long tests in the background and polls an exit file. This is the long-run exception of `dotnet-build-test` Rule 3 in `dev-essentials`.
- `gop-validate-compliance`, `gop-validate-security`, and `gop-validate-performance`: The blast radius of each agent now feeds a new lens. Security finds out whether untrusted input reaches the changed code through a caller. Performance finds out whether a caller calls the changed code in a loop or on a hot path. Compliance finds out whether the callers follow a changed contract as the plan or a skill requires.
- `gop-work`: The lookup of a merged pull request in the shared "Autonomy" section now uses the head `owner:branch` and the state `all`.
- `gop-work`: The `--interactive` routing now defines a partial dismissal and a repeated finding. A finding that the user dismissed does not make the status `BLOCKED` in a later cycle.

## dev-essentials 2.4.1, dotnet-backend-dev 1.2.1, and gop-pipeline 1.1.1 in release [2.4.1] - 2026-10-14

### Changed in dev-essentials

- All text in the changed skills, commands, and agents now follows plain-English rules. This means short sentences, active voice, one word for one meaning, and no filler. The workflow rules are the same. The notes below name what moved and where.
- `subagent-orchestration`: Moved the three worked examples to the new file `references/worked-examples.md`. Rule 3 no longer lists the parameters of the `Agent` tool, because the list was out of date. It still says that the tool has no `run_in_background` parameter.
- `review-loop`: Moved the `audit-team` adapter, which few runs need, to the new file `references/audit-team-adapter.md`. Moved the Full format into the reviewer brief file. The thread sections now exist once. The rules for the whole run now come before the late sections.
- `process-pr-comments`: Moved three procedures to the new files `references/commit-push-resolve.md`, `references/committed-fix-state.md`, and `references/deep-fix.md`. The briefs now name the skill files that a subagent must read.
- `feature-pipeline`: Moved four procedures to the new files `references/setup.md`, `references/checkpoint-protocol.md`, `references/commit-conventions.md`, and `references/cleanup.md`. The stage files and the artifact template now use the same rules for lint and for a failing test.
- `audit-personal-conventions`: Moved the report templates to the new file `references/report-templates.md`. The cleanup steps of Phase 9 now point to the cleanup reference file instead of repeating it.
- `bug-hunt` and its agents: Shortened repeated text, and fixed the numbering of one list in `SKILL.md`. Step 0 now uses the word "item" for its entries in all files.
- `trim-artifacts`: Moved the glob and regex instructions to the new file `references/protect-set.md`. Moved the script results to the new file `references/script-results.md`. Removed the section "Common failure modes".
- `git-worktree-management` and `merge-worktree-projects`: Shortened repeated text. Workflow D now says where `owner` and `repo` come from.
- `implement-task`, `implement-batch`, and `research-implement-review-report`: The three files now share one list for the division of labor. The guardrails no longer repeat the autonomy rules.
- `implement`, `opsx-implement`, and `save-context`: Removed repeated guardrails. `save-context` now states the output path for `--change` and `--plan`.
- `create-html-artifact` and `help-review-pr`: Shortened the text. `create-html-artifact` now says which mermaid tests run in which pass.
- `create-documentation`: Moved the four document templates to the new files `templates/feature.md`, `templates/configuration.md`, `templates/rest-api.md`, and `templates/migration.md`. A run reads only the template that it needs.
- `write-markdown`: Removed paths of another repository and two copies of the `markdownlint` commands.
- `write-tests`, `compose-pr`, `task-composer`, `docs-composer`, and the audit commands and agents: Removed repeated guardrails and infrastructure nouns from the examples. `audit-team` now passes two guardrails to its review agents.
- `engineering-discipline`, `dotnet-build-test`, `github-mcp-conventions`, `git-sync`, and `project-claude-md-preamble`: Shortened the text and removed a pointer to a section that does not exist.
- The shared "Autonomy" section in all workflows: Rewrote one condition so that it follows the plain-English rules. The meaning is the same.

### Fixed in dev-essentials

- `feature-pipeline`: A security-review finding that is `[HIGH]` and blocking now counts as a blocking issue. It goes to the fix round. With `--autonomous`, a remaining one stops the run before the push. Before, only `review.md` counted.
- `create-html-artifact`: The `mmdc` run and the `_test-mermaid.html` page run only in a fix pass. The grep counts always run.
- `help-review-pr` and `github-mcp-conventions`: The GitHub MCP parameter names now match the tool schemas, for example `pullNumber` and `perPage`.
- `github-mcp-conventions`: Rule 4 no longer says that no MCP tool can discard a pending review. It tells the agent not to discard or edit comments through MCP, and to use the GitHub UI.
- `git-sync`: The fix recipe now puts the saved commits back as a range. Several commits above the broken commit are now safe.
- `process-pr-comments`: A non-trivial `[Optional]` comment whose direction the comment or the code settles is now implemented, as for `[Suggestion]`. The decline draft is only for comments that nothing settles.
- `bug-hunt`: In the default mode, the run no longer waits for an "OK" that never comes. With `--interactive`, it still waits.

### Changed in dotnet-backend-dev

- `dotnet-conventions`, `handle-sensitive-data`, and `model-mapping`: The text now follows plain-English rules. Removed a repeated section and a stale claim from `dotnet-conventions`.
- `add-migration`: Moved the common patterns to the new file `references/common-patterns.md`.
- `add-configuration-option`, `create-controller`, `create-ef-entity`, and `update-swagger-spec`: Shortened the text and replaced `mermaid` fences that held no diagram.
- `create-tests`: Removed the code and the lists in `SKILL.md` that repeat the example files. Added a checklist of the seven enforced gates. The gates apply to every test class, and the text now says so.
- `create-domain-model`, `create-exception`, `create-primitive-wrapper`, `create-string-resource`, and `add-session-logging`: The text now follows plain-English rules, and the examples use neutral business nouns and full method bodies.

### Fixed in dotnet-backend-dev

- `update-swagger-spec`: The controller sketch now says that the class name, the base class, and the try-catch rule come from `create-controller`.
- `create-ef-entity`: An application service is created for each case in the list, also for validation across entities. Before, one line named only orchestration.
- `add-configuration-option`: Helm is now an example. The checklist works for any deployment system.

### Changed in gop-pipeline

- `gop-work`: Moved the routing for `--interactive` to the new file `references/interactive-routing.md`. The text now follows plain-English rules.
- The eight `gop-` agents: The text now follows plain-English rules. The five validators now run `git diff HEAD`, so they read both the staged and the unstaged changes.

### Fixed in gop-pipeline

- `gop-work`: After the second re-run cycle, the run starts no third cycle. If only warnings remain, it goes to Phase 5 and lists the warnings in the final report.
- `gop-work`: The text now uses the tool name `Agent`, not the old name `Task`.

## dev-essentials 2.4.0 and gop-pipeline 1.1.0 in release [2.4.0] - 2026-10-13

### Added in dev-essentials

- `save-context`: Added Step 5, a light cleanup of the context and handoff files of the session. It runs by default, and `--no-cleanup` turns it off. It deletes finished context files that git does not track. It trims files that open work still needs, updates facts that are no longer true, and fixes links to deleted files. It asks before it deletes a file from an older session or a branch. If another command runs the steps of `save-context`, the cleanup does not run.

### Changed in dev-essentials

- Workflows with decision gates now run without a stop at those gates by default. Deletion of data, posts to outside systems, push, and pull request creation still wait for the user. The new flag `--interactive` brings back every gate. The new flag `--autonomous` removes every stop, also before deletion, posts, push, and pull request creation. It does not add steps: a push that needs `--push` still needs it. It merges only where a workflow has a merge step and the branch policy allows a merge without a review. If the work cannot continue without an answer, the workflow asks in every mode. Each workflow carries the same "Autonomy" section.
- Without `--autonomous`, the workflows ask about a critical decision that has no ground in the plan. With `--autonomous`, they choose the option that follows the plan and the existing code, and list the decision in the final report for review. They do not destroy git work that has no other copy, for example a branch with unmerged commits or uncommitted changes. One exception: a squash merge makes `git branch -d` refuse a branch whose content is in the base branch. Two conditions must be true before they delete such a branch with `git branch -D`. First, its pull request is merged (read through the GitHub MCP tools). Second, the local tip equals the head SHA of that pull request. Else they keep the branch and list it in the final report. This rule does not cover a context file that a cleanup step classifies for deletion.
- The change covers 13 workflows. Commands: `research-implement-review-report`, `implement-task`, `implement-batch`, `implement`, `opsx-implement`, and `save-context`. Skills: `review-loop`, `feature-pipeline`, `process-pr-comments`, `audit-personal-conventions`, `bug-hunt`, `trim-artifacts`, and `git-worktree-management`.
- `review-loop`: Without `--interactive`, the run does not wait at the Phase 4 triage. With `--autonomous`, it also decides a finding that is not clear-cut. It lists the decision in the new Phase 9 section "Decisions for your review".
- `process-pr-comments`: By default, it implements larger fixes and non-trivial suggestions whose approach or direction the comment or the code settles. The new parameter `interactive` brings back draft-and-wait. `autonomous` covers question and discussion replies, design-level fixes, and push. It now also creates `[OutOfScope]` issues through Task Composer without a question. If both `interactive` and `autonomous` are set, the skill asks once which mode to use.
- `feature-pipeline`: Human Approve #1 stops only with `--interactive`. In the default mode, Task Comment #1 waits for Human Approve #2, which stops. With `--interactive` or `--autonomous`, the run posts Task Comment #1 before implementation. With `--autonomous`, Human Approve #2 stops in one case: blocking issues remain after the automatic fix round. Without `--interactive`, one automatic fix round runs before Human Approve #2 shows open blocking issues.
- `audit-personal-conventions`: Phase 5 approves the recommended C, D, and E items by default and defers the rest. Phase 9a asks once before it writes stubs. With `--autonomous`, no Phase 9 gate stops. This includes the per-repo push gate. The precondition tests before each gate still run.
- `engineering-discipline` Rule 2: If an auto-approved plan grounds a critical decision in the task, the code, or the documentation, the plan covers it. Else the decision stays a question for the user. With `--autonomous`, the agent chooses the option that follows the plan and the existing code, and lists the decision for the user to review.
- `github-mcp-conventions` Rule 1: Without `--interactive`, a workflow that documents it (`bug-hunt`) can take `owner/repo` from the `origin` remote. It must report the value as taken from the remote.
- `subagent-orchestration`: A workflow that runs with its default autonomy uses Opus instead of a question about Fable. The run-format agreement can come from no objection.
- `subagent-orchestration`: Rule 5 now allows `SendMessage` to your own subagent by its agent ID. Use it to resume the subagent after a stop, or to correct it on the same task. The rule still forbids `name`, `team_name`, shared task lists, and messages between subagents. Rule 3 and the anti-patterns now say the same.
- `subagent-orchestration`: Replaced the section `Trust but verify` with three tiers. The orchestrator checks cheap facts, and an agent checks the content. Only before a high-risk action, the orchestrator re-reads the lines that the action depends on. The "Check scope" part of "Run format agreement" now points to these tiers.
- `process-pr-comments` and `audit-personal-conventions`: Replaced the claim that a subagent cannot get a follow-up message. The Claude Code docs show that `SendMessage` can resume a subagent.
- `save-context`: `Confirm to user` is now Step 6, and the next-session continuation prompt is now Step 7.
- `research-implement-review-report` and `implement-task`: The final report no longer ends with the next-session continuation prompt of `save-context`. The commands print the report only.
- `task-composer`: If the user ran a calling skill with `autonomous`, that skill can approve `mode: create` for the user.

### Removed in dev-essentials

- `save-context`: Removed the tip to use `--context <path>` with `/implement` or `/opsx-implement`.
- `review-loop`: Removed the flag `--auto-proceed`. The run waits at the Phase 4 triage only with `--interactive`.
- `process-pr-comments`: Removed the parameter `auto-push`. To push without a question, ask for the push in the request. The parameter `autonomous` removes all gates of the skill.

### Changed in gop-pipeline

- `gop-work`: Without `--interactive`, Explore and Plan agents write the plan, and the run approves it. The run accepts every validation proposal with a confidence of 90% or more. When the result is `BLOCKED`, it also accepts every CRITICAL proposal. The push now waits for the approval of the user. With `--interactive`, Plan Mode and the old routing come back, and the plan approval covers the push. With `--autonomous`, no gate stops, and `gop-commit` pushes without a question.
- `gop-commit`: New input `push` (`yes` or `no`, default `no`).

## dev-essentials 2.3.0 in release [2.3.0] - 2026-10-13

### Added

- Added the skill `bug-hunt`. It runs a read-only bug hunt over a whole repository and saves one verified bug report. It exports the analyzed commit and the base branch with `git archive`. It splits the code into areas. It skips known bugs from notes files and GitHub issues. It never creates GitHub issues. Its step-0 meta-plan states the run format: the orchestrator checks only the structure of the report, and chat gets at most one status line for each step and one final report. A run context file keeps the stable facts of the run for the agents and for later rounds. The final chat report is saved as `bug-hunt-final-summary.md`. The user can turn off the base comparison, clone a newer base from the remote, and turn off experiments. The user can also set pause points with a scheduled resume.
- Added 8 reference files to the skill `bug-hunt`: `report-format.md`, `report-skeleton.md`, `plain-english-fallback.md`, `agent-briefs.md`, `structure-checks.md`, `pauses.md`, `inputs-and-meta-plan.md`, and `resume-and-failures.md`. Added the script `scripts/check_report.py`. It runs the structure checks of the report. It needs Python 3 and only its standard library.
- Added the agents `bug-hunter`, `bug-verifier`, and `bug-report-auditor`. One hunter searches each area in turn. Verifiers try to refute each finding and set a verdict. The auditor makes sure that the whole report is consistent. The hunters and verifiers can read public documentation, third-party sources, and GitHub data through read-only `gh` commands.
- Added the section "Run format agreement" to the skill `subagent-orchestration`. At the start of a long run, an orchestrating skill states what the orchestrator checks itself and what only the verifier or reviewer agents check. Chat gets at most one short status line for each phase and one final report. When the user agrees, this check scope replaces the generic "re-check every subagent claim" rules for that run only.

### Changed

- `review-loop`: States the run format after Phase 2. It applies from that statement unless the user objects. The Phase 4 acknowledgment gives the final agreement. With `--auto-proceed`, it applies without a stop. While it applies, chat gets one status line for each cycle, and the cycle reports go to files. If the user defines an end-of-run format, the final report uses it. When a calling workflow runs review-loop, the Phase 9 summary goes to that workflow.

## dev-essentials 2.2.0 in release [2.2.0] - 2026-10-11

### Added

- Added the skill `trim-artifacts`. It runs a trim pass on text artifacts. These include notes, plans, research, state files, handoff files, agent memory, logs, and task lists. It removes history, review records, process residue, and duplication. It keeps decisions, ids, needed facts with their sources, and uncertainty markers.
- Added 4 reference files and `scripts/trim_report.py` to the skill `trim-artifacts`. The script is written in Python and uses only the standard library. It compares the files before and after a trim. If a trim loses an id or a protected block, the script fails.

## gop-pipeline 1.0.2 in release [2.1.0] - 2026-08-31

### Fixed

- Gave the 8 pipeline agents a `description` field in their frontmatter. The agents are `gop-build`, `gop-commit`, `gop-test`, and the five `gop-validate-*` validators. The field says what each agent does and that it runs as a stage of the `gop-work` pipeline. This removes the 8 `claude plugin validate` warnings about agent frontmatter that had no `description`.

## dev-essentials 2.1.0 and dotnet-backend-dev 1.2.0 in release [2.1.0] - 2026-08-31

This release ported and generalized several skills, commands, and rule additions from a separate internal iteration of this toolkit. It stripped or transformed branding and tooling to fit the conventions of this marketplace. The release includes a full fidelity pass. The pass compared every skill, command, and agent against its upstream counterpart. It restored content that the port silently dropped. The release also includes a marketplace-wide de-branding cleanup.

### Added in dev-essentials

- Added these skills:
  - `audit-personal-conventions`: Performs a deep verification of personal/repo-convention drift. It has 2 worked examples and 4 reference files.
  - `create-html-artifact`: Renders a self-contained HTML report, plan, or review file. It has 4 reference files.
  - `project-claude-md-preamble`: Keeps the `CLAUDE.md` preamble of a project self-contained.
- Added the commands `help-review-pr`, `merge-worktree-projects`, `research-implement-review-report`, `implement-task`, and `implement-batch`. The command `help-review-pr` reviews a GitHub PR end-to-end and produces an HTML artifact. It can also post the findings as review comments.
- `feature-pipeline`: Added a new Stage 2b (`stages/plan-artifact.md`). The stage renders the approved implementation plan as an HTML artifact through `create-html-artifact` for Human Approve #1. Also added an anti-bypass gate, an archiving gate, and a commit-mode option.
- `review-loop`: Added an audit-team adapter, a `blocking` finding flag, and an orchestrated mode for large-target reviews (`references/orchestrated-review.md`).
- `process-pr-comments`: Added real wiring for resolving GitHub threads and a filter for resolved and outdated threads. Updated `references/thread-state-schema.md`.
- `engineering-discipline`: Added Rules 4–7: try/catch discipline, proof-before-claiming-done, an overblown-code guardrail, and refactor-scope discipline.
- `subagent-orchestration`: Fixed Rule 3. Added new Rules 5–7 and a model-selection matrix.
- `save-context`: Added a next-session continuation prompt.
- Added notes and sections to these skills and agents:
  - `create-documentation`
  - `git-sync`
  - `git-worktree-management`
  - `general-conventions` (documentation and PowerShell)
  - The `task-composer` agent (GitHub sub-issue create flow)

### Added in dotnet-backend-dev

- `create-tests`: Rewrote the mock-builder parameters to use `.ApplyIf`. A single `Create*` helper for each dependency takes optional nullable parameters. The helper applies them with `.ApplyIf`. This replaces the old overload-based pattern. Also added a new `enforced-gates.md` example.
- `dotnet-conventions`: Added notes to `ef-patterns.md` and `testing.md`.

### Changed in dev-essentials

- `review-loop`: Restored the shipped default configuration that the port dropped. The configuration has these parts:
  - 2 review cycles (not 3)
  - An Opus reviewer and a Sonnet fixer by default
  - A plan for each fix, made by the reviewer's tier before the fixer implements it
  - One commit per round
  - Merit-based (not label-based) triage
- `research-implement-review-report` and `implement-batch`: Updated the commands to describe the default configuration of `review-loop` accurately. They no longer imply a manual model override.
- `audit-team`: Replaced the non-functional foreground or background `mode` argument with a cross-reference to Rule 3 of `subagent-orchestration`. The `Agent` tool has no such mode.
- `process-pr-comments`: Restored the two-stage dispatch model. It has a read-only classifier stage and a judgment-bearing actor stage after it. It also has a hand-back to the orchestrating session for `deep-fix` cycles. Restored the contract for the Stage 1 report in `references/thread-state-schema.md`.

### Fixed in dev-essentials and dotnet-backend-dev

- Fidelity pass: Restored the content below from the upstream source. The initial port silently dropped it.
  - Rule 2 of `dotnet-build-test`: Restored the `--no-build` stale-referenced-binary caveat. A solution-level build can leave a test project that links an old DLL and report a false-green run. Restored the verbatim-proof reporting gate. Restored the guidance "warning-count deltas across incremental builds are meaningless".
  - `process-pr-comments`: Restored the rule for a carried-over unconfirmed-commit-claim thread. The skill resolves the thread automatically only after the human approves the resolve. The ancestry check alone does not resolve it. Made the `[OutOfScope]` issue-creation flow route through Task Composer consistently. Restored the safeguard "never defer reviewer-stated work without an `[OutOfScope]` tag" and its list of forbidden phrasing.
  - `feature-pipeline`: Restored the rationale for Project Context Injection. Restored the `{WORKTREE_PATH}` placeholder in the command that removes the worktree in Stage 10. The command regressed to a hardcoded relative path before this fix. Restored the trigger phrases and the rationale for bulk cleanup. Restored a concrete sandboxed-terminal example.
  - `git-worktree-management`: Restored the note that whoever runs the worktree removal workflow executes it and must not re-delegate it. Restored the note "bulk removal archives first, then removes per-path".
  - `github-mcp-conventions`: Restored a rule to make sure that a created issue relationship was actually applied. Restored a rule to read large PR diffs from local git, not from an MCP call that uses many tokens.
  - `create-tests`: Restored the dropped cross-reference "the same null-argument gate applies to methods". Restored a mixed static and instance test-helper example. Fixed an intro example that used `params` in violation of Rule 6 of the same skill.
  - Restored smaller passages in `opsx-implement`, `implement`, `help-review-pr`, `save-context`, `subagent-orchestration`, `git-sync`, and `engineering-discipline`.
- Completed the de-branding:
  - Replaced residual cloud-vendor identifiers (AWS, Azure, and Cosmos names) in the example code of `dotnet-backend-dev` with neutral business nouns. This covers `create-tests`, `add-migration`, `create-controller`, `model-mapping`, `update-swagger-spec`, and `dotnet-conventions/logging.md`.
  - Fixed a `DeploymentOptions` type-name collision in a `create-tests` example.
  - Replaced the remaining "work item" and Azure DevOps terminology across the marketplace with GitHub or provider-neutral equivalents.
  - Made the OpenSpec tracking-reference bullet of `save-context` specific to GitHub Issues and Projects.
- `dotnet-build-test` and `task-composer`: Fixed broken YAML frontmatter.

## dev-essentials 2.0.0 and dotnet-backend-dev 1.1.0 in release [2.0.0] - 2026-05-10

### Added in dev-essentials

- Added the skills `engineering-discipline`, `subagent-orchestration`, `git-sync`, `dotnet-build-test`, `review-loop`, and `github-mcp-conventions`. The skill `review-loop` came with 4 reference files and 2 worked examples.
- `review-loop`: Kept the trigger phrases `/review-loop` and `/review-pr` in the frontmatter description. GitHub MCP replaced ADO MCP for `target=pr` mode.
- `process-pr-comments`: Added `references/automated-review-verification.md`, which replaces `air-verification.md`. Added a GitHub-native phase flow (`pull_request_read`, `add_reply_to_pull_request_comment`) and a configurable bot-author list.
- `feature-pipeline`: Added a Pipeline Discipline section (3 safeguards). Added a note on Safeguard 2 in Human Approve #2, and a `pr` field in the schema of `pipeline-state.json`. Added gated worktree removal in Step 10 through GitHub MCP.
- Audit commands (`audit-plan`, `audit-openspec`, `audit-team`): Added a guardrail that requires verification before a fix.

### Added in dotnet-backend-dev

- `create-tests`: Added the section Constructor Null-Argument Tests (foreach-over-List\<Action\> pattern, anti-pattern: boolean stripes). Added the section Scenario Tests (stubs only, no mocking). Added the section Test Scope and Props Files.
- `create-tests/examples`: Added `constructor-null-arg-tests.md` and `scenario-tests.md`.

### Changed in dev-essentials

- `task-composer` agent: Rewrote the agent with three modes (draft, response, and create). Added a GitHub issue workflow (`issue_write` and `issue_read`). The workflow has two steps: create the issue, then make sure that it was created. Added a cross-reference to Rule 1 of `github-mcp-conventions`.
- `git-worktree-management`: Added a new path scheme `.claude/worktrees/<branch>/`, bootstrap steps, PR-status discovery through GitHub MCP (Workflow D), and a keep-until-PR-merged lifecycle.
- `process-pr-comments`: Rewrote the skill on top of GitHub MCP throughout. Removed the legacy work-item-ID prefix from the commit message. Changed the thread anchors to use `html_url`. Changed the `[OutOfScope]` tracking to use `issue_write` for tracking-issue creation. Updated `references/thread-state-schema.md` to GitHub field names.
- `feature-pipeline` Step 0: Changed worktree creation to delegate to Workflow A of `git-worktree-management`. It no longer uses inline git commands.
- Skill cross-references: Removed legacy upstream prefixes from all cross-reference names.

### Removed in dev-essentials

- Removed the commands `review-loop.md` and `review-pr.md`. The trigger phrases now live in the frontmatter description of the skill `review-loop`.
- Removed `process-pr-comments/references/air-verification.md`. The file `automated-review-verification.md` replaces it.

### Breaking changes in dev-essentials

- `task-composer` is now native to GitHub MCP. It calls `issue_write` and `issue_read` instead of any other PR-provider MCP tool. Existing non-GitHub workflows break.
- `process-pr-comments` now works only with GitHub MCP. It requires the GitHub MCP server. Existing non-GitHub workflows break.
- Deleted the commands `/dev-essentials:review-loop` and `/dev-essentials:review-pr`. Use the skill `review-loop` instead. Its description has the trigger phrases `/review-loop` and `/review-pr`.

## [1.0.2] - 2026-05-08

### Added

- `marketplace.json`: Added a top-level `description` so that the Discover tab shows a one-line summary.
- All 3 `plugin.json` manifests: Added `$schema`, a JSON Schema reference for editor validation. Added `repository`, a link back to this GitHub repository. Added per-plugin `keywords` for the Discover tab.
- `CLAUDE.md`: Added a Versioning Policy section. It has semver bump rules for each plugin, a single-source-of-truth rule for `version`, and an update-propagation flow.
- `README.md`: Added a Validating section that points at `claude plugin validate`. Added a References section that links the three official documentation pages for Claude Code plugins.

### Changed

- Bumped all 3 plugins from `1.0.0` to `1.0.1`. The manifest contract changed because of new metadata fields. We recommend that consumers re-fetch at the next `/plugin marketplace update`.
- `README.md`: Corrected the slash command from `/plugins marketplace add` to `/plugin marketplace add`. The singular form follows the current Claude Code documentation.
- `README.md` configuration examples: Replaced the undocumented shapes `plugins.marketplaces[]` and `plugins.sources[]` with the documented `extraKnownMarketplaces` and `enabledPlugins` configuration. The examples use `"source": "git"` with no `.git` suffix on the URL. This matches what Claude Code writes on install.
- `README.md` schema examples: Added a top-level `description` to the `marketplace.json` example and removed the per-plugin `version` from it. Added `$schema`, `repository`, and `keywords` to the `plugin.json` example.

### Removed

- `marketplace.json`: Removed the per-plugin `version` field from each entry inside `plugins[]`. Plugin versions live only in each `plugin.json`. This follows the new Versioning Policy.

### Fixed

- `README.md`, section "Installing a single plugin": Corrected the name of the configuration file from `.claude/settings.json` to `.claude/settings.local.json`. The file name now matches the file that the marketplace-add snippet above this section targets. This stops users from defining `extraKnownMarketplaces` in two different configuration files.

## [1.0.1] - 2026-05-04

### Changed

- Renamed the marketplace from `vasar-claude-marketplace` to `vasar-plugins-marketplace`. The new name matches the data model of Claude Code. The file `marketplace.json` lists plugins, so "plugins" is the more accurate name for the category.
- Updated all repository URL references in `README.md` and `CHANGELOG.md` to the new GitHub URL. The GitHub repository was renamed in the Web UI. Git redirects the old URL automatically.

### Fixed

- `README.md` schema example for `plugin.json`: Removed the directory-string fields `skills`, `agents`, and `commands` (for example `"./skills/"`). The example now mirrors the metadata-only manifests that this repository ships. It also explains that Claude Code discovers components automatically from the default locations.

## [1.0.0] - 2026-05-04

### Added

- Added the initial marketplace layout with three plugins:
  - `dev-essentials` has four composer agents (PR, Task, Test, Docs), ten workflow commands, and seven cross-stack skills. The skills cover markdown, XML docs, git worktrees, PR review comments, feature pipeline, general conventions, and `create-documentation`.
  - `dotnet-backend-dev` has fifteen .NET, Clean Architecture, DDD, EF Core, OpenAPI, and Mapperly skills. It also has a backend conventions hub with nine topic references. The topics are controllers, services, configuration, domain models, EF patterns, logging, mappers, security, and testing.
  - `gop-pipeline` is the Git Operations Pipeline workflow. The stages run in this order: `plan`, `implement`, `build`, `test`, `validate`, `commit`. It has five parallel validator subagents for correctness, reuse, security, compliance, and performance. It also has build, test, and commit agents.
- Added the repository artifacts:
  - A README with install instructions and an authoring reference
  - An MIT LICENSE
  - A root `CLAUDE.md` with documentation-first guardrails and repository conventions
  - This CHANGELOG
  - `.gitignore`
- Added the manifest layout. The file `.claude-plugin/marketplace.json` lists the three plugins. Each `plugin.json` declares only metadata (name, version, description, author). It relies on Claude Code to discover components automatically at the documented default locations: `skills/`, `commands/`, and `agents/`.

[Unreleased]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.2.0...HEAD
[4.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.1.1...v4.2.0
[4.1.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.1.0...v4.1.1
[4.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.10.0...v4.0.0
[3.10.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.9.0...v3.10.0
[3.9.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.8.0...v3.9.0
[3.8.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.7.0...v3.8.0
[3.7.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.5...v3.7.0
[3.6.5]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.4...v3.6.5
[3.6.4]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.3...v3.6.4
[3.6.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.2...v3.6.3
[3.6.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.1...v3.6.2
[3.6.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.6.0...v3.6.1
[3.6.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.5.0...v3.6.0
[3.5.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.4.0...v3.5.0
[3.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.3.1...v3.4.0
[3.3.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.3.0...v3.3.1
[3.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.3...v3.3.0
[3.2.3]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.2...v3.2.3
[3.2.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.1...v3.2.2
[3.2.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.2.0...v3.2.1
[3.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.1.1...v3.2.0
[3.1.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.1.0...v3.1.1
[3.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.0.2...v3.1.0
[3.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v3.0.0...v3.0.1
[3.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.5.0...v3.0.0
[2.5.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.2...v2.5.0
[2.4.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.1...v2.4.2
[2.4.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.4.0...v2.4.1
[2.4.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/releases/tag/v1.0.0
