#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/inventory-fixture.sh"

make_inventory_repo
git checkout -q -b work/seeded-defects
fixture_publish work/seeded-defects
dotnet_warm Inventory.sln
