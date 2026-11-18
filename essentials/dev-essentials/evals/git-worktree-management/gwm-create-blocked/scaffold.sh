#!/usr/bin/env bash
set -euo pipefail

lib="$(dirname "${BASH_SOURCE[0]}")/../../_lib"
source "$lib/git-fixture.sh"
source "$lib/py-fixture.sh"

make_pager_repo
# The repository ignores the worktree folder, so the run needs no change of the exclude file.
printf '.claude/worktrees/\n' >> .gitignore
fixture_commit "ignore the worktree folder"
fixture_publish main
