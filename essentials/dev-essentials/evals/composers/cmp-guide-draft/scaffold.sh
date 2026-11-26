#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
fixture_notes_folder
fixture_write docs/drafts/release-steps.md <<'CASE_EOF'
# Release the pager package

This draft guide shows the maintainers how to release a new version. Nobody reviewed it yet.

## Steps

1. Run the tests.
2. Tag the release commit.
CASE_EOF
fixture_commit "add a draft guide"
fixture_publish main
