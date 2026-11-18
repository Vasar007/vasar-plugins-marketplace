#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

make_inventory_repo
fp_write_context with-provider
# This case has a PR command, so that Step 9 opens the PR that Step 9b tries to merge.
sed -i 's/^- \*\*PR creation:\*\* none$/- **PR creation:** `mcp__plugin_github_github__create_pull_request`/' .claude/feature-pipeline-context.md
grep -q 'create_pull_request' .claude/feature-pipeline-context.md
# The mock of pull_request_read gives this commit as the head of the PR. A test pins its SHA.
fixture_commit "add the pipeline context"
git checkout -q -b work/merge-gate
fixture_publish work/merge-gate
dotnet_warm Inventory.sln
