#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/dotnet-fixture.sh"
source "$lib/billing-fixture.sh"

make_billing_repo
git checkout -q -b work/tests
dotnet_warm Billing.sln
