#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

SCRATCH_CONTENT='scratch notes: ask the team about the shelf labels'

make_inventory_repo
fixture_notes_folder
fp_write_context with-provider
# This case has a PR command, so that a grader can see the PR call of Stage 9.
sed -i 's/^- \*\*PR creation:\*\* none$/- **PR creation:** `mcp__plugin_github_github__create_pull_request`/' .claude/feature-pipeline-context.md
grep -q 'create_pull_request' .claude/feature-pipeline-context.md
fixture_commit "add the pipeline context"
git checkout -q -b work/untracked-file
fixture_publish work/untracked-file
printf '%s' "$SCRATCH_CONTENT" > scratch.txt
dotnet_warm Inventory.sln
