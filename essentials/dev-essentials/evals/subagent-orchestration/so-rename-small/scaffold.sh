#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"
source "$lib/commit-log.sh"

make_users_repo 6
fixture_publish main
fixture_log_commits
