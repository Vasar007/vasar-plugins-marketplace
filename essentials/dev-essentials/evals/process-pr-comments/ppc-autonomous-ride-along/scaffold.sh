#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
add_paging_branch
fixture_publish feature/paging 42:feature/paging
# A local commit of the author that is not pushed yet. Only its body has T#9101, so it names no thread.
printf '\nPages are 1-based. Page 1 holds the first items.\n' >> README.md
fixture_commit $'Say in the README that pages are 1-based\n\nThe review thread T#9101 is about the bounds of a page. This note makes the paging rule clear.'
