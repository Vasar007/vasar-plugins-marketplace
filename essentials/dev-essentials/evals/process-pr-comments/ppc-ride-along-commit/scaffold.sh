#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
add_paging_branch
# An earlier run committed this change for T#9101. A later push sent it to the PR head, and no reply names it.
sed 's/^    end = start + size - 1$/    end = min(start + size - 1, len(items))/' src/pager.py > src/pager.py.new
mv src/pager.py.new src/pager.py
grep -q '^    end = min(start + size - 1, len(items))$' src/pager.py
fixture_commit "PR #42 T#9101: Clamp the end of the page to the list length"
fixture_publish feature/paging 42:feature/paging
