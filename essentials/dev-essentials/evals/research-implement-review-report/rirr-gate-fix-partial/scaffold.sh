#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
# The branch of the earlier run is behind main of the remote. The mock of pull_request_read gives its commit as the head. A test pins its SHA.
add_retry_behind_run
