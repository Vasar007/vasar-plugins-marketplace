#!/usr/bin/env bash
# The project context of the feature-pipeline eval cases. A scaffold sources this file after git-fixture.sh.
#
# fp_write_context <with-provider|no-provider>: writes .claude/feature-pipeline-context.md for the Inventory fixture.
# The caller commits the file with fixture_commit. The no-provider variant leaves out the Task Provider section.
# REVIEW.md is not in the Guidance Files on purpose, so that the review must find it on its own.
set -euo pipefail

fp_write_context() {
    local variant="${1:-}"
    case "$variant" in
        with-provider | no-provider) ;;
        *)
            echo "fp_write_context: the argument must be with-provider or no-provider" >&2
            return 1
            ;;
    esac
    {
        cat <<'FP_EOF'
# Feature Pipeline — Project Context

FP_EOF
        if [ "$variant" = "with-provider" ]; then
            cat <<'FP_EOF'
## Task Provider

- **Name:** GitHub Issues
- **MCP server prefix:** `mcp__plugin_github_github__`
- **Project / organization:** `example-org/inventory`

FP_EOF
        fi
        cat <<'FP_EOF'
## Worktree

- **Branch template:** `work/{task-id}`
- **Allowed variables:** `{task-id}`

## Repository

- **Type:** git
- **Base branch:** `main`
- **Solution / root path:** `./Inventory.sln`

## Commands

- **Build:** `dotnet build Inventory.sln -m:1`
- **Test:** `dotnet test Inventory.sln -m:1`
- **Push:** `git push -u origin HEAD`
- **PR creation:** none

## Guidance Files

- `CLAUDE.md`

## Key Conventions

- Package versions are in `Directory.Packages.props`.

## Artifacts Directory

- `.pipeline`
FP_EOF
    } | fixture_write .claude/feature-pipeline-context.md
}
