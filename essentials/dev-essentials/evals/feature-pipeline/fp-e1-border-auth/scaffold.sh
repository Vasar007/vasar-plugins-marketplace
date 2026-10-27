#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

make_inventory_repo
fp_write_context with-provider
fixture_commit "add the pipeline context"
git checkout -q -b work/border-auth
fixture_publish work/border-auth
dotnet_warm Inventory.sln
