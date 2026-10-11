# Changelog

This file records all notable changes to this marketplace.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for each plugin separately.
For the current version of a plugin, see the `plugin.json` file of that plugin.
In each release heading, the linked number is the release tag of the marketplace, for example `v2.1.0`.
The other numbers in a heading are plugin versions.

## [Unreleased]

No changes yet.

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

- `README.md` schema example for `plugin.json`: Removed the directory-string fields `skills`, `agents`, and `commands` (for example `"./skills/"`). Claude Code interprets them as file paths and rejects them on install. The example now mirrors the metadata-only manifests that this repository ships. It also explains that Claude Code discovers components automatically from the default locations.

## [1.0.0] - 2026-05-04

### Added

- Added the initial marketplace layout with three plugins:
  - `dev-essentials` has four composer agents (PR, Task, Test, Docs), ten workflow commands, and seven cross-stack skills. The skills cover markdown, XML docs, git worktrees, PR review comments, feature pipeline, general conventions, and `create-documentation`.
  - `dotnet-backend-dev` has fifteen .NET, Clean Architecture, DDD, EF Core, OpenAPI, and Mapperly skills. It also has a backend conventions hub with nine topic references. The topics are controllers, services, configuration, domain models, EF patterns, logging, mappers, security, and testing.
  - `gop-pipeline` is the Git Operations Pipeline workflow. The stages run in this order: plan, implement, build, test, validate, commit. It has five parallel validator subagents for correctness, reuse, security, compliance, and performance. It also has build, test, and commit agents.
- Added the repository artifacts:
  - A README with install instructions and an authoring reference
  - An MIT LICENSE
  - A root `CLAUDE.md` with documentation-first guardrails and repository conventions
  - This CHANGELOG
  - `.gitignore`
- Added the manifest layout. The file `.claude-plugin/marketplace.json` lists the three plugins. Each `plugin.json` declares only metadata (name, version, description, author). It relies on Claude Code to discover components automatically at the documented default locations: `skills/`, `commands/`, and `agents/`.

[Unreleased]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/releases/tag/v1.0.0
