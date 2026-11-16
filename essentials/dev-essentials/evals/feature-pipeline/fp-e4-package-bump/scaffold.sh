#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"
source "$lib/pipeline-fixture.sh"

INVENTORY_NUNIT_VERSION="4.6.1"

make_inventory_repo
fp_write_context with-provider
fixture_commit "add the pipeline context"
git checkout -q -b work/package-bump
fixture_publish work/package-bump
# The run has no network. So dotnet_warm also puts NUnit 5.0.0, the version of the issue, into the NuGet folder of the run.
dotnet_warm Inventory.sln NUnit@5.0.0
