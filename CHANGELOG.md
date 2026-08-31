# Changelog

All notable changes to this marketplace are tracked here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
on a per-plugin basis (see each plugin's `plugin.json` for its current version).

## [Unreleased]

_No changes yet._

## dev-essentials [2.1.0] — dotnet-backend-dev [1.2.0] — 2026-08-31

Ported and generalized several skills, commands, and rule additions from a
separate internal iteration of this toolkit — branding and tooling stripped
or transformed to fit this marketplace's conventions.

### Added — dev-essentials

- New skills: `audit-personal-conventions` (deep verification of
  personal/repo-convention drift, with 2 worked examples + 4 reference
  files), `create-html-artifact` (renders a self-contained HTML report/plan/
  review file, with 4 reference files), `project-claude-md-preamble` (keeps
  a project's `CLAUDE.md` preamble self-contained).
- New commands: `help-review-pr` (end-to-end GitHub PR review producing an
  HTML artifact, optionally posting findings as review comments),
  `merge-worktree-projects`, `research-implement-review-report`,
  `implement-task`, `implement-batch`.
- `feature-pipeline`: new Stage 2b (`stages/plan-artifact.md`) renders the
  approved implementation plan as an HTML artifact via `create-html-artifact`
  for Human Approve #1; anti-bypass gate, archiving gate, and a commit-mode
  option.
- `review-loop`: audit-team adapter, a `blocking` finding flag, and an
  orchestrated mode for large-target reviews (`references/orchestrated-
  review.md`).
- `process-pr-comments`: real GitHub thread-resolve wiring plus a resolved/
  outdated thread filter; `references/thread-state-schema.md`.
- `engineering-discipline`: Rules 4–7 (try/catch discipline, proof-before-
  claiming-done, overblown-code guardrail, refactor-scope discipline).
- `subagent-orchestration`: Rule 3 fix plus new Rules 5–7 and a model-
  selection matrix.
- `save-context`: next-session continuation prompt.
- Additive notes/sections in `create-documentation`, `git-sync`,
  `git-worktree-management`, `general-conventions` (documentation/
  PowerShell), and the `task-composer` agent (GitHub sub-issue create flow).

### Added — dotnet-backend-dev

- `create-tests`: `.ApplyIf` mock-builder-param rewrite (single `Create*`
  helper per dependency takes optional nullable params applied via
  `.ApplyIf`, replacing the old overload-based pattern) and a new
  `enforced-gates.md` example.
- `dotnet-conventions`: additive notes in `ef-patterns.md` and
  `testing.md`.

### Fixed

- `dotnet-build-test` and `task-composer`: broken YAML frontmatter.

### Added — dev-essentials

- New skills: `engineering-discipline`, `subagent-orchestration`, `git-sync`, `dotnet-build-test`, `review-loop` (with 4 reference files + 2 worked examples), `github-mcp-conventions`.
- `review-loop`: trigger phrases `/review-loop` and `/review-pr` preserved in frontmatter description; GitHub MCP replaces ADO MCP for `target=pr` mode.
- `process-pr-comments`: new `references/automated-review-verification.md` (replaces `air-verification.md`); GitHub-native phase flow (pull_request_read, add_reply_to_pull_request_comment); configurable bot-author list.
- `feature-pipeline`: Pipeline Discipline section (3 safeguards), Safeguard 2 note in Human Approve #2, `pr` field in `pipeline-state.json` schema, gated Step 10 worktree removal via GitHub MCP.
- Audit commands (`audit-plan`, `audit-openspec`, `audit-team`): verify-before-fix guardrail.

### Added — dotnet-backend-dev

- `create-tests`: Constructor Null-Argument Tests section (foreach-over-List\<Action\> pattern, anti-pattern: boolean stripes), Scenario Tests section (stubs-only, no mocking), Test Scope and Props Files section.
- `create-tests/examples`: `constructor-null-arg-tests.md`, `scenario-tests.md`.

### Changed — dev-essentials

- `task-composer` agent: three-mode rewrite (draft/response/create), GitHub issue workflow (issue_write + issue_read), two-step create-then-verify, cross-reference to `github-mcp-conventions` Rule 1.
- `git-worktree-management`: new path scheme `.claude/worktrees/<branch>/`, bootstrap steps, GitHub MCP PR-status discovery (Workflow D), keep-until-PR-merged lifecycle.
- `process-pr-comments`: rewritten on top of GitHub MCP throughout; commit message drops the legacy work-item-ID prefix; thread anchors use `html_url`; `[OutOfScope]` tracking uses `issue_write` for tracking-issue creation; `references/thread-state-schema.md` updated to GitHub field names.
- `feature-pipeline` Step 0: worktree creation delegates to `git-worktree-management` Workflow A instead of inline git commands.
- Skill cross-references: legacy upstream prefixes removed from all cross-ref names.

### Removed — dev-essentials

- Commands `review-loop.md` and `review-pr.md` (trigger phrases now live in `review-loop` skill frontmatter description).
- `process-pr-comments/references/air-verification.md` (replaced by `automated-review-verification.md`).

### Breaking — dev-essentials

- `task-composer` is now GitHub-MCP-native: calls `issue_write` / `issue_read` instead of any other PR-provider MCP tool. Existing non-GitHub workflows break.
- `process-pr-comments` is now GitHub-MCP-only; requires the GitHub MCP server. Existing non-GitHub workflows break.
- `/dev-essentials:review-loop` and `/dev-essentials:review-pr` commands deleted; use the `review-loop` skill (`/review-loop` or `/review-pr` trigger phrases in description).

## [1.0.2] - 2026-05-08

### Added

- `marketplace.json`: top-level `description` so the Discover tab shows a one-line summary.
- All 3 `plugin.json` manifests: `$schema` (JSON Schema reference for editor validation), `repository` (links back to this GitHub repo), and per-plugin `keywords` for the Discover tab.
- `CLAUDE.md`: new **Versioning Policy** section — semver bump rules per plugin, single-source-of-truth rule for `version`, and update-propagation flow.
- `README.md`: a **Validating** section pointing at `claude plugin validate`, and a **References** section linking the three official Claude Code plugin docs pages.

### Changed

- All 3 plugins bumped from `1.0.0` → `1.0.1`. The manifest contract changed (new metadata fields), so consumers should re-fetch on next `/plugin marketplace update`.
- `README.md` slash command corrected: `/plugins marketplace add` → `/plugin marketplace add` (singular, per current Claude Code docs).
- `README.md` settings examples: replaced the undocumented `plugins.marketplaces[]` / `plugins.sources[]` shapes with the documented `extraKnownMarketplaces` + `enabledPlugins` settings, using `"source": "git"` (no `.git` URL suffix, matching what Claude Code writes on install).
- `README.md` schema examples: `marketplace.json` example now includes top-level `description` and drops per-plugin `version`; `plugin.json` example now includes `$schema`, `repository`, and `keywords`.

### Removed

- `marketplace.json`: per-plugin `version` field on each entry inside `plugins[]`. Plugin versions live only in each `plugin.json` (per the new Versioning Policy).

### Fixed

- `README.md` "Installing a single plugin" section: corrected the settings file name from `.claude/settings.json` to `.claude/settings.local.json` so it matches the file targeted by the marketplace-add snippet above it (avoids users defining `extraKnownMarketplaces` in two different settings files).

## [1.0.1] - 2026-05-04

### Changed

- Renamed marketplace from `vasar-claude-marketplace` to `vasar-plugins-marketplace`. The new name matches Claude Code's data model — `marketplace.json` lists plugins, so "plugins" is the more accurate categorical descriptor.
- All repository URL references in `README.md` and `CHANGELOG.md` updated to the new GitHub URL. The GitHub repository was renamed in the Web UI; Git auto-redirects the old URL.

### Fixed

- `README.md` `plugin.json` schema example: removed `skills` / `agents` / `commands` directory-string fields (e.g. `"./skills/"`), which Claude Code interprets as file paths and rejects on install. The example now mirrors the metadata-only manifests this repo ships and explains that components are auto-discovered from the default locations.

## [1.0.0] - 2026-05-04

### Added

- Initial marketplace layout with three plugins:
  - **`dev-essentials`** — four composer agents (PR, Task, Test, Docs), ten workflow commands, and seven cross-stack skills (markdown, XML docs, git worktrees, PR review comments, feature pipeline, general conventions, create-documentation).
  - **`dotnet-backend-dev`** — fifteen .NET / Clean Architecture / DDD / EF Core / OpenAPI / Mapperly skills plus a backend conventions hub with nine topic references (controllers, services, configuration, domain models, EF patterns, logging, mappers, security, testing).
  - **`gop-pipeline`** — Git Operations Pipeline workflow (plan → implement → build → test → validate → commit) with five parallel validator subagents (correctness, reuse, security, compliance, performance) plus build, test, and commit agents.
- Repo artifacts: README with install instructions and authoring reference, MIT LICENSE, root `CLAUDE.md` with documentation-first guardrails and repo conventions, this CHANGELOG, and `.gitignore`.
- Manifest layout: `.claude-plugin/marketplace.json` lists the three plugins; each `plugin.json` declares only metadata (name, version, description, author) and relies on Claude Code's auto-discovery for components at the documented default locations (`skills/`, `commands/`, `agents/`).

[Unreleased]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/releases/tag/v1.0.0
