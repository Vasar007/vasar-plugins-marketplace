# Feature Pipeline — Project Context

> **Setup:** copy this file to `<repo-root>/.claude/feature-pipeline-context.md`
> and fill in the placeholders below. The pipeline loads this file first; any
> missing required field falls back to CLAUDE.md derivation, then to asking
> the user.

## Task Provider

- **Name:** <provider display name, e.g. Azure DevOps, Jira, GitHub Issues>
- **MCP server prefix:** <tool-name prefix to look up capabilities, e.g. `mcp__azure-devops__` or `mcp__jira__`>
- **Project / organization:** <project identifier, e.g. `Backup` on your Azure DevOps host>

## Worktree

- **Branch template:** <e.g. `feature/{task-id}-{slug}` or `release/{username}/task-{task-id}`>
- **Allowed variables:** `{task-id}`, `{slug}`, `{username}` — list only the ones your template actually uses

## Repository

- **Type:** git
- **Base branch:** <e.g. `main`, `develop`, `release/1.0/master`>
- **Solution / root path:** <e.g. `./Sources/MyService.sln` or `./src/`>

## Commands

- **Pre-build** (optional, runs before the build gate): <command or empty>
- **Build:** <e.g. `dotnet build ./Sources/MyService.sln -c Debug`>
- **Test:** <e.g. `dotnet test ./Sources/Tests/MyService.Tests/MyService.Tests.csproj`>
- **Lint (optional):** <e.g. `dotnet format --verify-no-changes`>
- **Push:** <e.g. `git push -u origin HEAD`>
- **PR creation:** <e.g. `mcp__azure-devops__repo_create_pull_request` / `gh pr create`>

## Guidance Files

<!-- Repo-relative paths to any guidance docs the pipeline should read alongside the task description. -->
- `CLAUDE.md`
- <add more if applicable>

## Architecture Docs

<!-- Repo-relative paths to architecture / design docs. -->
- <e.g. `Docs/Architecture.md`>

## Testing Docs

<!-- Optional. Repo-relative paths to test-strategy or fixture-usage docs. -->
- <e.g. `Docs/Testing.md` or leave empty>

## Key Conventions

<!-- Short bullets. Anything the pipeline agents must know that is NOT already in CLAUDE.md. -->
- <e.g. "All PRs must link an ADO work item via `AB#<id>` in the title">
- <e.g. "Commit messages use the format `#<task-id> - <summary>`">
- <add more as needed>

## Artifacts Directory

<!-- Optional. Repo-relative directory for pipeline intermediate files (requirements.md, spec.md, review.md, etc.). Defaults to `tasks` if absent. -->
- <e.g. `Notes/Tasks` or leave empty>
