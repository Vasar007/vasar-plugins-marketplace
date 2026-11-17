#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

make_inventory_repo
fp_write_context with-provider
# The PR creation entry names the repository of the PR and the owner of a fork, so the head of the PR call is <owner>:<branch>.
sed -i 's|^- \*\*PR creation:\*\* none$|- **PR creation:** `mcp__plugin_github_github__create_pull_request` for `example-org/inventory`, fork owner `eval-user`|' .claude/feature-pipeline-context.md
grep -q 'fork owner `eval-user`$' .claude/feature-pipeline-context.md
fixture_commit "add the pipeline context"
git checkout -q -b work/fork-pr
fixture_publish work/fork-pr
dotnet_warm Inventory.sln
