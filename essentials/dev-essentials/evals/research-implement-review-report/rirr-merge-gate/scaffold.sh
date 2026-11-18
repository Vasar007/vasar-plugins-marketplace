#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_users_repo 6
printf 'notes/\n' >> .gitignore
fixture_commit "ignore the notes folder"
# The mock of pull_request_read gives this commit as the head of the pull request. A test pins its SHA.
git checkout -q -b work/retry-gate
fixture_publish work/retry-gate
