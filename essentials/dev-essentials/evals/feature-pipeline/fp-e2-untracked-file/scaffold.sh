#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

SCRATCH_CONTENT='scratch notes: ask the team about the shelf labels'

make_inventory_repo
fp_write_context with-provider
fixture_commit "add the pipeline context"
git checkout -q -b work/untracked-file
fixture_publish work/untracked-file
printf '%s' "$SCRATCH_CONTENT" > scratch.txt
dotnet_warm Inventory.sln
