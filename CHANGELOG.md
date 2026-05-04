# Changelog

All notable changes to this marketplace are tracked here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
on a per-plugin basis (see each plugin's `plugin.json` for its current version).

## [Unreleased]

_No changes yet._

## [1.0.0] - 2026-05-04

### Added

- Initial marketplace layout with three plugins:
  - **`dev-essentials`** — four composer agents (PR, Task, Test, Docs), ten workflow commands, and seven cross-stack skills (markdown, XML docs, git worktrees, PR review comments, feature pipeline, general conventions, create-documentation).
  - **`dotnet-backend-dev`** — fifteen .NET / Clean Architecture / DDD / EF Core / OpenAPI / Mapperly skills plus a backend conventions hub with nine topic references (controllers, services, configuration, domain models, EF patterns, logging, mappers, security, testing).
  - **`gop-pipeline`** — Git Operations Pipeline workflow (plan → implement → build → test → validate → commit) with five parallel validator subagents (correctness, reuse, security, compliance, performance) plus build, test, and commit agents.
- Repo artifacts: README with install instructions and authoring reference, MIT LICENSE, root `CLAUDE.md` with documentation-first guardrails and repo conventions, this CHANGELOG, and `.gitignore`.
- Manifest layout: `.claude-plugin/marketplace.json` lists the three plugins; each `plugin.json` declares only metadata (name, version, description, author) and relies on Claude Code's auto-discovery for components at the documented default locations (`skills/`, `commands/`, `agents/`).

[Unreleased]: https://github.com/Vasar007/vasar-claude-marketplace/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Vasar007/vasar-claude-marketplace/releases/tag/v1.0.0
