# Changelog

All notable changes to this marketplace are tracked here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
on a per-plugin basis (see each plugin's `plugin.json` for its current version).

## [Unreleased]

_No changes yet._

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

[Unreleased]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Vasar007/vasar-plugins-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Vasar007/vasar-plugins-marketplace/releases/tag/v1.0.0
