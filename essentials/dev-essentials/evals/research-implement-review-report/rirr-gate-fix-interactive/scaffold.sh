#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
# The commit of the earlier run fails only the lint job of CI. The mock of pull_request_read gives it as the head. A test pins its SHA.
add_retry_lint_run
