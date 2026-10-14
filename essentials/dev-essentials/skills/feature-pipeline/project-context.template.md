# Feature Pipeline — Project Context

> **Setup:** copy this file to `<repo-root>/.claude/feature-pipeline-context.md`, and fill in the placeholders below. The pipeline loads this file first. For a missing required field, it falls back to `CLAUDE.md`, and then it asks the user.

## Task Provider

- **Name:** <provider display name, for example GitHub Issues, Jira, or Linear>
- **MCP server prefix:** <tool-name prefix for the capability lookup, for example `mcp__plugin_github_github__` or `mcp__jira__`>
- **Project / organization:** <project identifier, for example `my-org/my-repo` on GitHub>

## Worktree

- **Branch template:** <for example `feature/{task-id}-{slug}` or `release/{username}/task-{task-id}`>
- **Allowed variables:** `{task-id}`, `{slug}`, `{username}`. List only the ones that your template uses.

## Repository

- **Type:** git
- **Base branch:** <for example `main`, `develop`, or `release/1.0/master`>
- **Solution / root path:** <for example `./Sources/MyService.sln` or `./src/`>

## Commands

- **Pre-build** (optional, runs before the build gate): <command or empty>
- **Build:** <for example `dotnet build ./Sources/MyService.sln -c Debug`>
- **Test:** <for example `dotnet test ./Sources/Tests/MyService.Tests/MyService.Tests.csproj`>
- **File-scoped test** (optional): <command that runs one test file, or empty>
- **Coverage** (optional): <command or empty>
- **Lint (optional):** <for example `dotnet format --verify-no-changes`>
- **Lint fix** (optional): <command or empty>
- **Migration** (optional): <command or empty>
- **Push:** <for example `git push -u origin HEAD`>
- **PR creation:** <for example `mcp__plugin_github_github__create_pull_request` or `gh pr create`>

## Guidance Files

<!-- Repo-relative paths to the guidance docs that the pipeline reads with the task description. -->
- `CLAUDE.md`
- <more paths, or none>

## Architecture Docs

<!-- Repo-relative paths to architecture or design docs. -->
- <for example `Docs/Architecture.md`>

## Testing Docs

<!-- Optional. Repo-relative paths to docs on the test strategy or the fixture usage. -->
- <for example `Docs/Testing.md`, or leave empty>

## Key Conventions

<!-- Short bullets. Anything that the pipeline agents must know and that is NOT already in CLAUDE.md. -->
- <for example "All PRs must reference the tracking issue URL in the PR body">
- <for example "Commit messages use the format `#<task-id> - <summary>`">
- <add more as needed>

## Artifacts Directory

<!-- Optional. Repo-relative folder for the intermediate files of the pipeline (requirements.md, spec.md, review.md, and others). The default is `tasks`. -->
- <for example `Notes/Tasks`, or leave empty>
